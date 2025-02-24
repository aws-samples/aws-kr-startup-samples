import * as React from "react";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";

export default function TableActions({ 
  loading,
  selectedItems,
  onRefresh,
  onBulkDownload,
  onBulkDelete 
}) {
  return (
    <SpaceBetween direction="horizontal" size="xs">
      <Button
        onClick={onRefresh}
        iconName="refresh"
        loading={loading}
      />
      <Button
        disabled={selectedItems.length === 0}
        onClick={onBulkDownload}
      >
        {`Download (${selectedItems.length})`}
      </Button>
      <Button
        disabled={selectedItems.length === 0}
        onClick={onBulkDelete}
      >
        {`Delete (${selectedItems.length})`}
      </Button>
    </SpaceBetween>
  );
} 