import os
from FlagEmbedding import BGEM3FlagModel
from typing import List, Dict, Union
from collections import defaultdict
import torch
import numpy as np
from tqdm import tqdm


class BGEModel:
    def __init__(self, model_name='BAAI/bge-m3', use_fp16=True):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        use_fp16 = use_fp16 and torch.cuda.is_available()
        print(f"Using FP16: {use_fp16}")
        
        print("Loading bge...")
        self.bge = BGEM3FlagModel(model_name, use_fp16=use_fp16, device=self.device)
        print("Model loaded successfully.")
        
        self.tokenizer = self.bge.tokenizer

    def compute_lexical_matching_score(self, lexical_weights_1, lexical_weights_2):
        return self.bge.compute_lexical_matching_score(
            lexical_weights_1, lexical_weights_2
        )

    def tokenize(self, text_batch, padding=False, truncation=True, max_length=8192):  # Max length shall be equal to the window size
        self.tokenizer(
            text_batch,
            padding=padding,
            truncation=truncation,
            return_tensors="pt",
            max_length=max_length,
        )  # .to(self.bge.model.device)
        
    def decode(self, tokenized_batch, skip_special_tokens=True):
        return self.tokenizer.decode(tokenized_batch, skip_special_tokens=skip_special_tokens)

    @torch.no_grad()
    def encode(
        self,
        tokenized_sentences: Union[List[List[int]], List[int]],
        batch_size: int = 1,
        return_dense: bool = True,
        return_sparse: bool = True,
        return_colbert_vecs: bool = False,
    ) -> Dict:

        # if self.num_gpus > 1:
        #     batch_size *= self.num_gpus
        self.bge.model.eval()

        input_was_list = False
        if isinstance(tokenized_sentences[0], int):
            tokenized_sentences = [tokenized_sentences]
            input_was_list = True

        def _process_token_weights(token_weights: np.ndarray, input_ids: list):
            # convert to dict
            result = defaultdict(int)
            unused_tokens = set(
                [
                    self.tokenizer.cls_token_id,
                    self.tokenizer.eos_token_id,
                    self.tokenizer.pad_token_id,
                    self.tokenizer.unk_token_id,
                ]
            )
            for w, idx in zip(token_weights, input_ids):
                if idx not in unused_tokens and w > 0:
                    idx = str(idx)
                    if w > result[idx]:
                        result[idx] = w
            return result

        def _process_colbert_vecs(colbert_vecs: np.ndarray, attention_mask: list):
            # delete the vectors of padding tokens
            tokens_num = np.sum(attention_mask)
            return colbert_vecs[
                : tokens_num - 1
            ]  # we don't use the embedding of cls, so select tokens_num-1

        all_dense_embeddings, all_lexical_weights, all_colbert_vec = [], [], []
        for start_index in tqdm(
            range(0, len(tokenized_sentences), batch_size),
            desc="Inference Embeddings",
            disable=len(tokenized_sentences) < 16,
        ):
            # tokenized_batch = tokenized_sentences[start_index:start_index + batch_size]
            tokenized_batch = tokenized_sentences[start_index]
            # print(tokenized_batch)
            batch_data = {
                "input_ids": tokenized_batch[0].unsqueeze(0).to(self.device),
                "attention_mask": tokenized_batch[1].unsqueeze(0).to(self.device),
            }
            output = self.bge.model(
                batch_data,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert=return_colbert_vecs,
            )
            if return_dense:
                all_dense_embeddings.append(output["dense_vecs"].cpu().numpy())

            if return_sparse:
                token_weights = output["sparse_vecs"].squeeze(-1)
                all_lexical_weights.extend(
                    list(
                        map(
                            _process_token_weights,
                            token_weights.cpu().numpy(),
                            batch_data["input_ids"].cpu().numpy().tolist(),
                        )
                    )
                )

            if return_colbert_vecs:
                all_colbert_vec.extend(
                    list(
                        map(
                            _process_colbert_vecs,
                            output["colbert_vecs"].cpu().numpy(),
                            batch_data["attention_mask"].cpu().numpy(),
                        )
                    )
                )

        if return_dense:
            all_dense_embeddings = np.concatenate(all_dense_embeddings, axis=0)

        if return_dense:
            if input_was_list:
                all_dense_embeddings = all_dense_embeddings[0]
        else:
            all_dense_embeddings = None

        if return_sparse:
            if input_was_list:
                all_lexical_weights = all_lexical_weights[0]
        else:
            all_lexical_weights = None

        if return_colbert_vecs:
            if input_was_list:
                all_colbert_vec = all_colbert_vec[0]
        else:
            all_colbert_vec = None

        return {
            "dense_vecs": all_dense_embeddings,
            "lexical_weights": all_lexical_weights,
            "colbert_vecs": all_colbert_vec,
        }
