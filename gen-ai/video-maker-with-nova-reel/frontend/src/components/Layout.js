import * as React from "react";
import SideNavigation from "@cloudscape-design/components/side-navigation";

export default function Layout({ activeHref, onNavigate, children }) {
  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '280px' }}>
        <SideNavigation
          activeHref={activeHref}
          header={{ href: "#/", text: "Video Generation Service" }}
          onFollow={onNavigate}
          items={[
            { type: "link", text: "Generate", href: "#/generate" },
            { type: "link", text: "Outputs", href: "#/outputs" }
          ]}
        />
      </div>
      <div style={{ flex: 1, padding: '20px' }}>
        {children}
      </div>
    </div>
  );
} 