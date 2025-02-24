import * as React from "react";
import Layout from "./components/Layout";
import InvocationsTable from "./components/InvocationsTable";
import GenerateForm from "./components/GenerateForm";

export default function App() {
  const [activeHref, setActiveHref] = React.useState("#/outputs");

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
      case "#/outputs":
        return <InvocationsTable />;
      case "#/generate":
        return <GenerateForm />;
      default:
        return null;
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