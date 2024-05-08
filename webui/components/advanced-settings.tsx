import { useState } from "react";
import { ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label"; 
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

interface AdvancedSettingsProps {
  windowSize: number;
  setWindowSize: (value: number) => void;
  k: number;
  setK: (value: number) => void;
  denseWeight: number;
  setDenseWeight: (value: number) => void;
  highlightQuery: boolean;
  setHighlightQuery: (value: boolean) => void;
}

export default function AdvancedSettings({
  windowSize,
  setWindowSize,
  k,
  setK,
  denseWeight,
  setDenseWeight,
  highlightQuery,
  setHighlightQuery,
}: AdvancedSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Advanced Settings</h4>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="icon">
            <ChevronsUpDown size={16} />
            <span className="sr-only">Toggle</span>
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className="py-4">
        <div className="flex flex-wrap gap-4 gap-x-8">
          <div className="flex-1 min-w-[240px]">
            {/* <Label htmlFor="windowSize">Window size</Label> */}
            <div className="font-medium text-sm pb-1">Window size</div>
            <Select
              value={windowSize.toString()}
              onValueChange={(value) => setWindowSize(parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder={windowSize.toString()} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="128">128</SelectItem>
                <SelectItem value="256">256</SelectItem>
                <SelectItem value="512">512</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1 min-w-[240px]">
            {/* <Label htmlFor="k">Number of Results (k)</Label> */}
            <div className="font-medium text-sm pb-1">Number of Results (k)</div>
            <Input
              type="number"
              id="k"
              value={k}
              onChange={(e) => setK(parseInt(e.target.value))}
            />
          </div>
          <div className="flex-1 min-w-[240px]">
            {/* <Label htmlFor="denseWeight">Dense Retrieval Weight</Label> */}
            <div className="font-medium text-sm pb-1">Dense Retrieval Weight</div>
            <Input
              type="number"
              id="denseWeight"
              value={denseWeight}
              onChange={(e) => setDenseWeight(parseFloat(e.target.value))}
              step="0.1"
              min="0"
              max="1"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="highlightQuery"
              name="highlightQuery"
              checked={highlightQuery}
              onCheckedChange={(e) => setHighlightQuery(!highlightQuery)}
            />
            <Label htmlFor="highlightQuery">Highlight Query</Label>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
