import * as React from "react";
import CollectionPreferences from "@cloudscape-design/components/collection-preferences";
import { TABLE_CONFIG } from '../../constants/table';

export default function TablePreferences() {
  return (
    <CollectionPreferences
      title="Preferences"
      confirmLabel="Confirm"
      cancelLabel="Cancel"
      preferences={{
        pageSize: TABLE_CONFIG.ITEMS_PER_PAGE,
        contentDisplay: [
          { id: "invocation_id", visible: true },
          { id: "created_at", visible: true },
          { id: "updated_at", visible: true },
          { id: "prompt", visible: true },
          { id: "status", visible: true },
        ],
      }}
      pageSizePreference={{
        title: "Page size",
        options: [
          { value: TABLE_CONFIG.ITEMS_PER_PAGE, label: `${TABLE_CONFIG.ITEMS_PER_PAGE} resources` },
          { value: 20, label: "20 resources" },
        ],
      }}
      wrapLinesPreference={{}}
      stripedRowsPreference={{}}
      contentDensityPreference={{}}
      contentDisplayPreference={{
        options: [
          { id: "invocation_id", label: "Invocation ID", alwaysVisible: true },
          { id: "created_at", label: "Created At" },
          { id: "updated_at", label: "Updated At" },
          { id: "prompt", label: "Prompt" },
          { id: "status", label: "Status" },
        ],
      }}
      stickyColumnsPreference={{
        firstColumns: {
          title: "Stick first column",
          description: "Keep the first column visible when scrolling horizontally",
          options: [
            { label: "None", value: 0 },
            { label: "First column", value: 1 },
          ],
        },
        lastColumns: {
          title: "Stick last column",
          description: "Keep the last column visible when scrolling horizontally",
          options: [
            { label: "None", value: 0 },
            { label: "Last column", value: 1 },
          ],
        },
      }}
    />
  );
} 