import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface FileMetadata {
  file_hash: string;
  filename: string;
  tags: string;
  creation_time: string;
  modification_time: string;
  ml_synced: string;
  size: number;
}

interface FileTree {
  [key: string]: {
    metadata?: FileMetadata;
    children: FileTree;
  };
}

interface FileManagerContextValue {
  fileTree: FileTree;
  currentPath: string;
  setCurrentPath: (path: string) => void;
  refreshFileTree: () => void;
  uploadFile: (file: File) => Promise<void>;
  deleteFile: (path: string) => Promise<void>;
}

const FileManagerContext = createContext<FileManagerContextValue | undefined>(undefined);

export const useFileManager = () => {
  const context = useContext(FileManagerContext);
  if (!context) {
    throw new Error("useFileManager must be used within a FileManagerProvider");
  }
  return context;
};

interface FileManagerProviderProps {
  children: ReactNode;
}

export const FileManagerProvider: React.FC<FileManagerProviderProps> = ({ children }) => {
  const [fileTree, setFileTree] = useState<FileTree>({});
  const [currentPath, setCurrentPath] = useState("/data");

  useEffect(() => {
    refreshFileTree();
  }, []);

  const refreshFileTree = async () => {
    try {
      const response = await fetch("/api/proxy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ action: "search_by_metadata", metadata: { path: "/data" } }),
      });

      if (response.ok) {
        const data = await response.json();
        // console.log(data);
        const newFileTree: FileTree = {};

        data.doc_paths.forEach((path: string) => {
          const parts = path.split("/").slice(2);
          console.log(parts);
          let currentLevel = newFileTree;

          parts.forEach((part, index) => {
            if (index === parts.length - 1) {
              currentLevel[part] = { children: {} };
            } else {
              currentLevel[part] = currentLevel[part] || { children: {} };
              currentLevel = currentLevel[part].children;
            }
          });
        });

        const metadataPromises = data.doc_paths.map(async (path: string) => {
          const response = await fetch(`/api/proxy?action=get_doc_metadata&doc_path=${encodeURIComponent(path)}`);
          const metadata = await response.json();
          return { path, metadata };
        });

        const metadataResults = await Promise.all(metadataPromises);
        metadataResults.forEach(({ path, metadata }) => {
          const parts = path.split("/").slice(2);
          let currentLevel = newFileTree;

          parts.forEach((part: any, index: any) => {
            if (index === parts.length - 1) {
              currentLevel[part].metadata = metadata;
            } else {
              currentLevel = currentLevel[part].children;
            }
          });
        });

        // Sort the keys of the FileTree object alphabetically
        const sortedFileTree = sortObjectKeys(newFileTree);

        setFileTree(sortedFileTree);
      } else {
        throw new Error("Error fetching file tree");
      }
    } catch (error) {
      console.error("Error fetching file tree:", error);
    }
  };

  // Helper function to sort the keys of an object alphabetically
  const sortObjectKeys = (obj: { [key: string]: any }): { [key: string]: any } => {
    const sortedObj: { [key: string]: any } = {};
    const keys = Object.keys(obj).sort();

    for (const key of keys) {
      sortedObj[key] = {
        ...obj[key],
        children: sortObjectKeys(obj[key].children),
      };
    }

    return sortedObj;
  };

  const uploadFile = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/proxy", {
        method: "POST",
        body: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (response.ok) {
        refreshFileTree();
      } else {
        throw new Error("Error uploading file");
      }
    } catch (error) {
      console.error("Error uploading file:", error);
    }
  };

  const deleteFile = async (path: string) => {
    try {
      const response = await fetch("/api/proxy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ action: "delete_doc", doc_path: path }),
      });

      if (response.ok) {
        refreshFileTree();
      } else {
        throw new Error("Error deleting file");
      }
    } catch (error) {
      console.error("Error deleting file:", error);
    }
  };

  return (
    <FileManagerContext.Provider value={{ fileTree, currentPath, setCurrentPath, refreshFileTree, uploadFile, deleteFile }}>
      {children}
    </FileManagerContext.Provider>
  );
};