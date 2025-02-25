import * as React from "react";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import FormField from "@cloudscape-design/components/form-field";
import Textarea from "@cloudscape-design/components/textarea";
import Alert from "@cloudscape-design/components/alert";
import { generateVideo } from "../../utils/api";

export default function GenerateForm() {
  const [prompt, setPrompt] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [showSuccess, setShowSuccess] = React.useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await generateVideo(prompt);
      setShowSuccess(true);
      // Redirect to Outputs page after 3 seconds
      setTimeout(() => {
        window.location.hash = "#/outputs";
      }, 3000);
    } catch (error) {
      console.error("Failed to generate video:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box margin={{ bottom: "l" }}>
      <SpaceBetween size="l">
        <Header variant="h1">Generate Video</Header>
        
        {showSuccess && (
          <Alert
            dismissible
            onDismiss={() => setShowSuccess(false)}
            statusIconAriaLabel="Success"
            type="success"
          >
            Video generation request has been successfully submitted. 
            Redirecting to Outputs page...
          </Alert>
        )}

        <form onSubmit={handleSubmit} style={{ width: '100%' }}>
          <SpaceBetween size="l">
            <FormField
              label="Prompt"
              description="Enter a description of the video you want to generate"
              stretch
            >
              <Textarea
                value={prompt}
                onChange={({ detail }) => setPrompt(detail.value)}
                placeholder="Ex) Slow cam of a man middle age; 4k; Cinematic; in a sunny day; peaceful; highest quality; dolly in;"
                rows={3}
                stretch
              />
            </FormField>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <SpaceBetween direction="horizontal" size="xs">
                <Button 
                  variant="normal"
                  onClick={() => alert("AI 프롬프트 추천 기능이 곧 제공될 예정입니다.")}
                >
                  Generative AI Assist
                </Button>
                <Button 
                  variant="primary" 
                  type="submit"
                  loading={loading}
                  disabled={!prompt.trim() || loading}
                >
                  Generate
                </Button>
              </SpaceBetween>
            </div>
          </SpaceBetween>
        </form>
      </SpaceBetween>
    </Box>
  );
} 