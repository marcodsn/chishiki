import { Skeleton } from "@/components/ui/skeleton";

export function SearchResultSkeleton() {
  return (
    <div className="px-4 py-3 bg-muted/50 rounded-md mt-3">
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-3/4 mb-2" />
      <Skeleton className="h-4 w-1/2" />
      <div className="text-xs text-muted-foreground mt-2">
        <Skeleton className="h-4 w-1/4" />
      </div>
    </div>
  );
}
