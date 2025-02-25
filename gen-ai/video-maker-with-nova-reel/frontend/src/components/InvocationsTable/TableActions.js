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
  const handleDelete = async () => {
    try {
      if (typeof onBulkDelete === 'function') {
        await onBulkDelete(selectedItems);
        onRefresh();
      } else {
        console.error("onBulkDelete is not a function");
      }
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  const handleDownload = async () => {
    try {
      if (typeof onBulkDownload === 'function') {
        await onBulkDownload(selectedItems);
        console.log(`${selectedItems.length}개 항목 다운로드 완료`);
        alert(`${selectedItems.length}개 항목 다운로드 완료`);
      } else {
        console.error("onBulkDownload is not a function");
        alert("다운로드 기능이 제대로 설정되지 않았습니다.");
      }
    } catch (error) {
      console.error("Download failed:", error);
      alert("다운로드 중 오류가 발생했습니다: " + error.message);
    }
  };

  return (
    <SpaceBetween direction="horizontal" size="xs">
      <Button
        onClick={onRefresh}
        iconName="refresh"
        loading={loading}
      />
      <Button
        disabled={selectedItems.length === 0}
        onClick={handleDownload}
      >
        {`Download (${selectedItems.length})`}
      </Button>
      <Button
        disabled={selectedItems.length === 0}
        onClick={handleDelete}
      >
        {`Delete (${selectedItems.length})`}
      </Button>
    </SpaceBetween>
  );
}
