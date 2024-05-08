import torch

def passages_generator(text, tokenizer, window_size=2048, stride=0.75):
    start_pos = 0
    while len(text) >= window_size:
        tokens = tokenizer(
            text, return_tensors="pt", max_length=window_size, truncation=True
        )
        passage_ids = tokens["input_ids"][0]
        passage_mask = tokens["attention_mask"][0]
        end_pos = start_pos + len(tokenizer.decode(passage_ids, skip_special_tokens=True))
        yield passage_ids, passage_mask, start_pos, end_pos

        # Move the window
        text_to_skip = tokenizer.decode(
            passage_ids[: int(window_size * stride)], skip_special_tokens=True
        )
        start_pos += len(text_to_skip)
        text = text[len(text_to_skip) :]

    # Process the remaining text as the last passage if it's not empty
    if text.strip():
        tokens = tokenizer(text, return_tensors="pt", truncation=True)
        passage_ids = tokens["input_ids"][0]
        passage_mask = tokens["attention_mask"][0]
        end_pos = start_pos + len(tokenizer.decode(passage_ids, skip_special_tokens=True))
        yield passage_ids, passage_mask, start_pos, end_pos