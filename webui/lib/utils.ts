import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
};

export const formatDate = (date: string) => {
    const dateObj = new Date(date); // new Date(parseFloat(date) * 1000);
    const options: Intl.DateTimeFormatOptions = {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    };
    return dateObj.toLocaleString("it-IT", options).replace(",", " at");
};

const getMimeType = (fileExtension: string | undefined): string => {
    switch (fileExtension?.toLowerCase()) {
        case "pdf":
            return "application/pdf";
        case "txt":
            return "text/plain";
        case "jpg":
        case "jpeg":
            return "image/jpeg";
        case "png":
            return "image/png";
        case "wav":
            return "audio/wav";
        case "mp3":
            return "audio/mp3";
        case "ogg":
            return "audio/ogg";
        case "mp4":
            return "video/mp4";
        default:
            return "application/octet-stream";
    }
};

export const openFile = (
    docPath: string,
    setLoadingFiles: (loading: boolean) => void,
) => {
    setLoadingFiles(true);

    fetch(
        `/api/proxy?doc_path=${encodeURIComponent(docPath)}&action=download_file`,
        {
            method: "GET",
        },
    )
        .then((response) => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error("Network response was not ok.");
        })
        .then((blob) => {
            const fileExtension = docPath.split(".").pop()?.toLowerCase();
            let mimeType = "application/octet-stream";

            if (fileExtension) {
                mimeType = getMimeType(fileExtension);
            }

            const url = window.URL.createObjectURL(
                new Blob([blob], { type: mimeType }),
            );
            const fileName = docPath.split("/").pop() || "";
            window.open(url, fileName);
        })
        .catch((error) => {
            console.error(
                "There has been a problem with your fetch operation:",
                error,
            );
        })
        .finally(() => {
            setLoadingFiles(false);
        });
};

export const downloadFile = (docPath: string) => {
    fetch(
        `/api/proxy?action=download_file&doc_path=${encodeURIComponent(docPath)}`,
        {
            method: "GET",
        },
    )
        .then((response) => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error("Network response was not ok.");
        })
        .then((blob) => {
            const fileExtension = docPath.split(".").pop()?.toLowerCase();
            let mimeType = "application/octet-stream";

            if (fileExtension) {
                mimeType = getMimeType(fileExtension);
            }

            const fileName = docPath.split("/").pop() || "";
            const url = window.URL.createObjectURL(
                new Blob([blob], { type: mimeType }),
            );
            const link = document.createElement("a");
            link.href = url;
            link.download = fileName;
            link.click();
            window.URL.revokeObjectURL(url);
        })
        .catch((error) => {
            console.error(
                "There has been a problem with your fetch operation:",
                error,
            );
        });
};

export const openFileText = (docPath: string) => {
    fetch(
        `/api/proxy?action=get_doc_text&doc_path=${encodeURIComponent(docPath)}`,
        {
            method: "GET",
        },
    )
        .then((response) => response.json())
        .then((data) => {
            if (data.doc_text) {
                const blob = new Blob([data.doc_text], {
                    type: "text/plain;charset=utf-8",
                });
                const url = window.URL.createObjectURL(blob);
                window.open(url, "_blank"); // Open the text in a new tab
                window.URL.revokeObjectURL(url); // Clean up the blob URL
            } else {
                throw new Error("Document text not found");
            }
        })
        .catch((error) => {
            console.error(
                "There has been a problem with your fetch operation:",
                error,
            );
        });
};
