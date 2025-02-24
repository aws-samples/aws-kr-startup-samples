export const TABLE_CONFIG = {
  ITEMS_PER_PAGE: 20,
  BASE_COLUMN_DEFINITIONS: [
    {
      id: "invocation_id",
      header: "Invocation ID",
      cell: item => item.invocation_id,
      sortingField: "invocation_id",
      isRowHeader: true,
    },
    {
      id: "prompt",
      header: "Prompt",
      cell: item => item.prompt,
      sortingField: "prompt",
    },
    {
      id: "status",
      header: "Status",
      cell: item => item.status,
      sortingField: "status",
    },
    {
      id: "created_at",
      header: "Created At",
      cell: item => item.created_at,
      sortingField: "created_at",
    },
    {
      id: "updated_at",
      header: "Updated At",
      cell: item => item.updated_at,
      sortingField: "updated_at",
    }
  ],
  PREFERENCES: {
    pageSize: 20,
    contentDisplay: [
      { id: "invocation_id", visible: true },
      { id: "created_at", visible: true },
      { id: "updated_at", visible: true },
      { id: "prompt", visible: true },
      { id: "status", visible: true },
    ],
  }
}; 