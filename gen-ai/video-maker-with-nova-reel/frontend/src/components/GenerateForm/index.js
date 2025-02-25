import * as React from "react";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import FormField from "@cloudscape-design/components/form-field";
import Textarea from "@cloudscape-design/components/textarea";
import Alert from "@cloudscape-design/components/alert";
import HelpPanel from "@cloudscape-design/components/help-panel";
import Icon from "@cloudscape-design/components/icon";
import AppLayout from "@cloudscape-design/components/app-layout";
import PromptInput from "@cloudscape-design/components/prompt-input";
import Modal from "@cloudscape-design/components/modal";
import { generateVideo } from "../../utils/api";

export default function GenerateForm() {
  const [prompt, setPrompt] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [showSuccess, setShowSuccess] = React.useState(false);
  const [toolsOpen, setToolsOpen] = React.useState(false);
  const [chatValue, setChatValue] = React.useState("");

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

  const handleChatSubmit = () => {
    if (chatValue.trim()) {
      setChatValue("");
    }
  };

  return (
    <>
      <AppLayout
        content={
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
                        onClick={(e) => {
                          e.preventDefault(); // 폼 제출 방지
                          setToolsOpen(!toolsOpen);
                        }}
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

                  <div>
                      <div>
                      <h2>Tips for Effective Prompting:</h2>
                      </div>
                      
                      <h3>Prompt Structure</h3>
                      <ul>
                      <li>Describe the scene as a caption rather than a command</li>
                      <li>Separate details with semicolons (;)</li>
                      <li>Add camera movements at the beginning or end of your prompt</li>
                      <li>Keep prompts under 512 characters</li>
                      <li>Avoid negation words like "no", "not", "without"</li>
                      </ul>

                      <h3>Recommended Keywords</h3>
                      <p>
                      <code>4k</code>, <code>cinematic</code>, <code>high quality</code>, <code>detailed</code>, 
                      <code>realistic</code>, <code>slow motion</code>, <code>dolly zoom</code>
                      </p>

                      <h3>Refinement Techniques</h3>
                      <ul>
                      <li>Use consistent seed values when making small prompt changes</li>
                      <li>Generate multiple variations with different seeds once you're satisfied</li>
                      </ul>

                      <h3>Example Prompts</h3>
                      <pre>
        Slow cam of a man middle age; 4k; Cinematic; in a sunny day; peaceful; highest quality; dolly in;
                      </pre>
                      <pre>
        Closeup of a large seashell in the sand. Gentle waves flow around the shell. Camera zoom in.
                      </pre>
                  </div>

                  <div>
                      <h3>
                          Learn More{" "}
                          <Icon name="external" size="inherit" />
                      </h3>
                      <ul>
                          <li>
                          <a href="https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-generation.html" target="_blank" rel="noopener noreferrer">
                              Amazon Nova Reel prompting best practices
                          </a>
                          </li>
                          <li>
                          <a href="https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-image-prompts.html" target="_blank" rel="noopener noreferrer">
                              Image-based video generation prompts
                          </a>
                          </li>
                          <li>
                          <a href="https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-camera-control.html" target="_blank" rel="noopener noreferrer">
                              Camera controls
                          </a>
                          </li>
                      </ul>
                      </div>
                </SpaceBetween>
              </form>
            </SpaceBetween>
          </Box>
        }
        tools={
          <HelpPanel
            header={<h2>Amazon Nova Chat</h2>}
          >
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              height: 'calc(100vh - 120px)', 
              justifyContent: 'space-between' 
            }}>
              <div style={{ overflowY: 'auto' }}>
                {/* Chat messages will be displayed here */}
              </div>
              <div style={{ position: 'sticky', bottom: 0, backgroundColor: 'white', paddingTop: '16px' }}>
                <PromptInput
                  onChange={({ detail }) => setChatValue(detail.value)}
                  value={chatValue}
                  onSubmit={handleChatSubmit}
                  actionButtonAriaLabel="Send message"
                  actionButtonIconName="send"
                  ariaLabel="Prompt input with min and max rows"
                  maxRows={8}
                  minRows={3}
                  placeholder="Ask a question"
                />
              </div>
            </div>
          </HelpPanel>
        }
        toolsOpen={toolsOpen}
        onToolsChange={({ detail }) => setToolsOpen(detail.open)}
        navigationHide={true}
        toolsWidth="400"
      />
    </>
  );
} 