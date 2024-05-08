import { useState, useRef } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { FolderIcon, FileIcon, FileText, FileJson, UploadCloud, Plus, Download, RefreshCw, Trash2 } from "lucide-react";
import { useFileManager } from "@/contexts/FileManagerContext";
import { formatBytes, formatDate } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface FileMetadata {
  file_hash: string;
  filename: string;
  tags: string;
  creation_time: string;
  modification_time: string;
  ml_synced: string;
  size: number;
}

interface File {
  name: string;
  type: "file" | "directory";
  metadata?: FileMetadata;
}

export const FileManager: React.FC = () => {
  const { fileTree, currentPath, setCurrentPath, refreshFileTree, uploadFile, deleteFile } = useFileManager();
  const [confirmDeletePath, setConfirmDeletePath] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loadingFiles, setLoadingFiles] = useState<{ [key: string]: boolean }>({});

  const getFilesAndDirs = (path: string): File[] => {
    const parts = path.split("/").slice(2);
    let currentLevel = fileTree;

    parts.forEach((part) => {
      currentLevel = currentLevel[part].children;
    });

    return Object.entries(currentLevel).map(([name, { metadata, children }]) => ({
      name,
      type: Object.keys(children).length > 0 ? "directory" : "file",
      metadata,
    }));
  };

  const handleGoBack = () => {
    if (currentPath !== "/") {
      const parentPath = currentPath.substring(0, currentPath.lastIndexOf("/"));
      setCurrentPath(parentPath);
    }
  };

  const handleDirClick = (dirName: string) => {
    setCurrentPath(`${currentPath}/${dirName}`);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const handleDeleteFile = (path: string) => {
    setConfirmDeletePath(path);
  };

  const handleConfirmDelete = () => {
    if (confirmDeletePath) {
      deleteFile(confirmDeletePath);
      setConfirmDeletePath(null);
    }
  };

  const handleCancelDelete = () => {
    setConfirmDeletePath(null);
  };

  const openFile = (docPath: string) => {
    docPath = docPath.substring(1); // Remove leading slash
    setLoadingFiles((prevState) => ({ ...prevState, [docPath]: true }));

    fetch(`/api/proxy?doc_path=${encodeURIComponent(docPath)}&action=download_file`, {
      method: 'GET',
    })
      .then((response) => {
        if (response.ok) {
          return response.blob();
        }
        throw new Error('Network response was not ok.');
      })
      .then((blob) => {
        const fileExtension = docPath.split('.').pop()?.toLowerCase();
        let mimeType = 'application/octet-stream';

        if (fileExtension === 'pdf') {
          mimeType = 'application/pdf';
        } else if (fileExtension === 'txt') {
          mimeType = 'text/plain';
        } else if (fileExtension === 'jpg' || fileExtension === 'jpeg') {
          mimeType = 'image/jpeg';
        } else if (fileExtension === 'png') {
          mimeType = 'image/png';
        }

        const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
        const fileName = docPath.split('/').pop() || '';
        window.open(url, fileName);
      })
      .catch((error) => {
        console.error('There has been a problem with your fetch operation:', error);
      })
      .finally(() => {
        setLoadingFiles((prevState) => ({ ...prevState, [docPath]: false }));
      });
  };

  const openFileText = (docPath: string) => {
    docPath = docPath.substring(1); // Remove leading slash
    fetch(`/api/proxy?action=get_doc_text&doc_path=${encodeURIComponent(docPath)}`, {
      method: 'GET',
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.doc_text) {
          const blob = new Blob([data.doc_text], { type: 'text/plain;charset=utf-8' });
          const url = window.URL.createObjectURL(blob);
          window.open(url, '_blank'); // Open the text in a new tab
          window.URL.revokeObjectURL(url); // Clean up the blob URL
        } else {
          throw new Error('Document text not found');
        }
      })
      .catch((error) => {
        console.error('There has been a problem with your fetch operation:', error);
      });
  };

  const getFileIcon = (filename: string) => {
    const extension = filename.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'txt':
        return <FileText className="inline-block mr-2 h-[1.2rem] w-[1.2rem]" />;
      case 'json':
        return <FileJson className="inline-block mr-2 h-[1.2rem] w-[1.2rem]" />;
      // Add more cases for other file types
      default:
        return <FileIcon className="inline-block mr-2 h-[1.2rem] w-[1.2rem]" />;
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex space-x-2">
          <Button size="icon" onClick={handleUploadClick}>
            <Plus className="h-[1.2rem] w-[1.2rem]" />
            <span className="sr-only">Upload</span>
          </Button>
          <Button variant="ghost" size="icon">
            <UploadCloud className="h-[1.2rem] w-[1.2rem]" />
            <span className="sr-only">Upload</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={refreshFileTree}>
            <RefreshCw className="h-[1.2rem] w-[1.2rem]" />
            <span className="sr-only">Refresh</span>
          </Button>
        </div>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          onChange={handleFileUpload}
        />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Last Modified</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {currentPath !== "/" && (
            <TableRow>
              <TableCell colSpan={4}>
                <h4 className="text-sm font-semibold cursor-pointer hover:underline" onClick={handleGoBack}>
                  ..
                </h4>
              </TableCell>
            </TableRow>
          )}
          {getFilesAndDirs(currentPath).map((file) => (
            <TableRow key={file.name}>
              <TableCell>
                <div className="flex items-center space-x-2">
                  {file.type === "directory" ? (
                    <h4
                      className="text-sm font-medium cursor-pointer hover:underline"
                      onClick={() => handleDirClick(file.name)}
                    >
                      <FolderIcon className="inline-block mr-2 h-[1.2rem] w-[1.2rem]" />
                      {file.name}
                    </h4>
                  ) : (
                    <h4 className="text-sm font-medium cursor-pointer hover:underline" onClick={() => openFile(`${currentPath}/${file.name}`)}>
                      {getFileIcon(file.name)}
                      {file.name}
                    </h4>
                  )}
                  {loadingFiles[`${currentPath}/${file.name}`.substring(1)] && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-foreground border-t-transparent"></div>
                  )}
                </div>
              </TableCell>
              <TableCell>{file.metadata?.size ? formatBytes(file.metadata.size) : "-"}</TableCell>
              <TableCell>{file.metadata?.modification_time ? formatDate(file.metadata.modification_time) : "-"}</TableCell>
              <TableCell>
                <div className="flex space-x-2">
                  {file.type === "file" && (
                    <Button variant="ghost" size="sm" className="w-9 p-0" onClick={() => openFileText(`${currentPath}/${file.name}`)}>
                      <FileText className="h-4 w-4" />
                      <span className="sr-only">Open Text</span>
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" className="w-9 p-0">
                    <Download className="h-4 w-4" />
                    <span className="sr-only">Download</span>
                  </Button>
                  {file.type === "file" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-9 p-0"
                      onClick={() => handleDeleteFile(`${currentPath}/${file.name}`)}
                    >
                      <Trash2 className="h-4 w-4" />
                      <span className="sr-only">Delete</span>
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={confirmDeletePath !== null} onOpenChange={handleCancelDelete}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Delete File</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this file? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              Delete
            </Button>
            <Button variant="outline" onClick={handleCancelDelete}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};