import { useState, useRef } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { FolderIcon, FileIcon, FileText, FileJson, UploadCloud, Plus, Download, RefreshCw, Trash2 } from "lucide-react";
import { useFileManager } from "@/contexts/FileManagerContext";
import { formatBytes, formatDate, openFile, openFileText, downloadFile } from "@/lib/utils";
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
    if (currentPath !== "/data") {
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
    <div className="py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex space-x-2">
          <Button onClick={handleUploadClick}>
            <UploadCloud className="h-[1rem] w-[1rem]" />
            <span className="ml-2">Upload</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={refreshFileTree}>
            <RefreshCw className="h-[1rem] w-[1rem]" />
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
      {/* <Table className="border border-separate border-tools-table-outline rounded-md"> */}
      <div className="overflow-x-auto rounded-md border">
        <Table className="">
          <TableHeader className="bg-muted/50">  {/* or bg-muted/50 */}
            <TableRow className="">
              <TableHead className="w-1/2">Name</TableHead>
              <TableHead className="">Size</TableHead>
              <TableHead className="">Last Modified</TableHead>
              <TableHead className="">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {currentPath !== "/data" && (
              <TableRow>
                <TableCell colSpan={4}>
                  <h4 className="text-sm font-semibold cursor-pointer hover:underline" onClick={handleGoBack}>
                    <FolderIcon className="inline-block mr-2 h-[1.2rem] w-[1.2rem] fill-foreground" />
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
                        <FolderIcon className="inline-block mr-2 h-[1.2rem] w-[1.2rem] fill-foreground" />
                        {file.name}
                      </h4>
                    ) : (
                      <h4 className="text-sm font-medium cursor-pointer hover:underline" onClick={() => openFile(`${currentPath}/${file.name}`, (loading) => setLoadingFiles((prevState) => ({ ...prevState, [`${currentPath}/${file.name}`]: loading })))}>
                        {getFileIcon(file.name)}
                        {file.name}
                      </h4>
                    )}
                    {loadingFiles[`${currentPath}/${file.name}`] && (
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

                    {file.type === "file" && (
                      <Button variant="ghost" size="sm" className="w-9 p-0" onClick={() => downloadFile(`${currentPath}/${file.name}`)}>
                        <Download className="h-4 w-4" />
                        <span className="sr-only">Download</span>
                      </Button>
                    )}
                    {file.type === "file" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-9 p-0 hidden"
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
      </div>

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