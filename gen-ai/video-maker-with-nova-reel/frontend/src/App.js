import * as React from "react";
import Layout from "./components/Layout";
import ImageGenerateForm from "./components/ImageGenerateForm";
import InvocationsTable from "./components/InvocationsTable";
import GenerateForm from "./components/GenerateForm";
import Storyboard from "./components/Storyboard";

export default function App() {
  const [activeHref, setActiveHref] = React.useState("#/video/outputs");

  // Handle navigation
  const handleNavigation = (event) => {
    if (!event.detail.external) {
      event.preventDefault();
      setActiveHref(event.detail.href);
    }
  };

  // Render content based on active route
  const renderContent = () => {
    switch (activeHref) {
      case "#/":
      case "#/image":
      case "#/image/generate":
        return <ImageGenerateForm />;
      case "#/video":
      case "#/video/outputs":
        return <InvocationsTable />;
      case "#/video/generate":
        return <GenerateForm />;
      case "#/video/storyboard":
        return <Storyboard />;
      default:
        return <InvocationsTable />; // 기본값을 Outputs로 설정
    }
  };

  return (
    <Layout
      activeHref={activeHref}
      onNavigate={handleNavigation}
    >
      {renderContent()}
    </Layout>
  );
}