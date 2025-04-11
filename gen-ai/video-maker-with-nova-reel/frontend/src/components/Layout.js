import * as React from "react";
import SideNavigation from "@cloudscape-design/components/side-navigation";

export default function Layout({ activeHref, onNavigate, children }) {
  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '280px' }}>
        <SideNavigation
          activeHref={activeHref}
          header={{ href: "#/", text: "Video Generation Service" }}
          onFollow={(event) => {
            console.log('Menu clicked:', event.detail.href);
            onNavigate(event);
          }}
          items={[
            { type: "link", text: "Image Generate", href: "#/image/generate" },
            { type: "link", text: "Video Generate", href: "#/video/generate" },
            { type: "link", text: "Video Storyboard", href: "#/video/storyboard" },
            { type: "link", text: "Video Outputs", href: "#/video/outputs" }
          ]}
        />
      </div>
      <div style={{ flex: 1, padding: '20px' }}>
        {children}
      </div>
    </div>
  );
} 