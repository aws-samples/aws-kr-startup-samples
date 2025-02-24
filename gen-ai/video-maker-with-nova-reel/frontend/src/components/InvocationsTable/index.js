import * as React from "react";
import Table from "@cloudscape-design/components/table";
import TextFilter from "@cloudscape-design/components/text-filter";
import Pagination from "@cloudscape-design/components/pagination";
import Button from "@cloudscape-design/components/button";
import { useCollection } from '@cloudscape-design/collection-hooks';
import { TABLE_CONFIG } from '../../constants/table';
import { fetchVideos, downloadVideo } from '../../utils/api';
import TableHeader from './TableHeader';
import TablePreferences from './TablePreferences';
import StatusIndicator from "@cloudscape-design/components/status-indicator";

export default function InvocationsTable() {
  // State management for pagination
  const [currentPage, setCurrentPage] = React.useState(1);
  const [pagesCount, setPagesCount] = React.useState(1);
  const [pageData, setPageData] = React.useState({});
  const [nextToken, setNextToken] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [selectedItems, setSelectedItems] = React.useState([]);

  // Current page data (empty array if no data)
  const currentPageData = pageData[currentPage] || [];

  const { items, filteredItemsCount, collectionProps, filterProps } = useCollection(
    currentPageData,
    {
      filtering: {
        empty: "No resources found",
        noMatch: "No matches found",
        filteringPlaceholder: "Find resources",
      },
      pagination: { pageSize: TABLE_CONFIG.ITEMS_PER_PAGE },
      sorting: {
        defaultState: {
          sortingColumn: {
            sortingField: "created_at",
          },
          isDescending: true,
        }
      },
      selection: {}
    }
  );

  // Fetch page data
  const fetchPage = async (token, page) => {
    setLoading(true);
    try {
      const data = await fetchVideos(TABLE_CONFIG.ITEMS_PER_PAGE, token);
      const videos = data.videos.map((video) => ({
        invocation_id: video.invocation_id,
        prompt: video.prompt,
        status: video.status,
        created_at: video.created_at,
        updated_at: video.updated_at
      }));

      setPageData(prev => ({ ...prev, [page]: videos }));
      setCurrentPage(page);
      
      if (data.nextToken) {
        setNextToken(data.nextToken);
        setPagesCount(page + 1);
      } else {
        setNextToken(null);
        setPagesCount(page);
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Initial data fetch
  React.useEffect(() => {
    fetchPage(null, 1);
  }, []);

  // Handle page change
  const handlePageChange = ({ detail }) => {
    const newPage = detail.currentPageIndex;
    if (newPage === currentPage) return;
    
    if (pageData[newPage]) {
      setCurrentPage(newPage);
    } else {
      fetchPage(nextToken, newPage);
    }
  };

  // Handle refresh
  const handleRefresh = () => {
    fetchPage(null, 1);
  };

  // Handle bulk download
  const handleBulkDownload = async () => {
    try {
      for (const item of selectedItems) {
        await fetchVideos(item.invocation_id);
      }
    } catch (error) {
      console.error("Bulk download failed:", error);
    }
  };

  // Handle single item download
  const handleDownload = async (invocationId) => {
    try {
      await downloadVideo(invocationId);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  const columnDefinitions = [
    ...TABLE_CONFIG.BASE_COLUMN_DEFINITIONS.slice(0, 2),
    {
      id: "status",
      header: "Status",
      cell: item => {
        const statusProps = {
          Completed: { type: "success" },
          Failed: { type: "error" },
          InProgress: { type: "info" }
        }[item.status] || { type: "pending" };

        return (
          <StatusIndicator {...statusProps}>
            {item.status}
          </StatusIndicator>
        );
      },
      minWidth: 120
    },
    ...TABLE_CONFIG.BASE_COLUMN_DEFINITIONS.slice(3),
    {
      id: "actions",
      header: "Actions",
      cell: item => (
        <Button
          variant="inline-link"
          onClick={() => handleDownload(item.invocation_id)}
          ariaLabel={`Download ${item.invocation_id}`}
        >
          Download
        </Button>
      ),
      minWidth: 170
    }
  ];

  return (
    <Table
      {...collectionProps}
      items={items}
      loading={loading}
      loadingText="Loading resources"
      selectionType="multi"
      selectedItems={selectedItems}
      onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
      columnDefinitions={columnDefinitions}
      resizableColumns
      header={
        <TableHeader
          selectedItems={selectedItems}
          totalItems={currentPageData.length}
          loading={loading}
          onRefresh={handleRefresh}
          onBulkDownload={handleBulkDownload}
        />
      }
      filter={
        <TextFilter
          {...filterProps}
          countText={`${filteredItemsCount} matches`}
          filteringPlaceholder="Find resources"
        />
      }
      pagination={
        <Pagination
          currentPageIndex={currentPage}
          pagesCount={pagesCount}
          onChange={handlePageChange}
        />
      }
      preferences={<TablePreferences />}
      ariaLabels={{
        selectionGroupLabel: "Resource selection",
        allItemsSelectionLabel: ({ selectedItems }) =>
          `${selectedItems.length} ${
            selectedItems.length === 1 ? "item" : "items"
          } selected`,
        itemSelectionLabel: ({ selectedItems }, item) =>
          `${item.invocation_id} is ${
            selectedItems.includes(item) ? "" : "not "
          }selected`
      }}
    />
  );
} 