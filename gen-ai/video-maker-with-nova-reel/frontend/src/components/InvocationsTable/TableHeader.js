import * as React from "react";
import Header from "@cloudscape-design/components/header";
import TableActions from "./TableActions";

export default function TableHeader({
  selectedItems,
  totalItems,
  loading,
  onRefresh,
  onBulkDownload,
  onBulkDelete
}) {
  return (
    <Header
      actions={
        <TableActions
          loading={loading}
          selectedItems={selectedItems}
          onRefresh={onRefresh}
          onBulkDownload={onBulkDownload}
          onBulkDelete={onBulkDelete}
        />
      }
    >
      <Header
        counter={
          selectedItems.length 
            ? `(${selectedItems.length}/${totalItems})`
            : `(${totalItems})`
        }
      >
        Outputs
      </Header>
    </Header>
  );
} 