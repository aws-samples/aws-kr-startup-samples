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
import FileUpload from "@cloudscape-design/components/file-upload";
import ChatBubble from "@cloudscape-design/chat-components/chat-bubble";
import Avatar from "@cloudscape-design/chat-components/avatar";
import ReactMarkdown from 'react-markdown';
import { generateVideo, chatNova } from "../../utils/api";

export default function GenerateForm() {
  const [prompt, setPrompt] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [showSuccess, setShowSuccess] = React.useState(false);
  const [toolsOpen, setToolsOpen] = React.useState(false);
  const [chatValue, setChatValue] = React.useState("");
  const [chatMessages, setChatMessages] = React.useState([]);
  const [imageData, setImageData] = React.useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = React.useState(null);
  const [selectedFiles, setSelectedFiles] = React.useState([]);
  const [imageError, setImageError] = React.useState(null);

  const validateImageDimensions = (dataUrl) => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        if (img.width === 1280 && img.height === 720) {
          setImageError(null);
          resolve(true);
        } else {
          const errorMsg = `이미지 해상도가 1280x720이 아닙니다. 현재 해상도: ${img.width}x${img.height}`;
          setImageError(errorMsg);
          reject(new Error(errorMsg));
        }
      };
      img.onerror = () => {
        setImageError("이미지를 불러오는 중 오류가 발생했습니다.");
        reject(new Error("Image load error"));
      };
      img.src = dataUrl;
    });
  };

  const handleFileChange = (event) => {
    const files = event.detail.value;
    setSelectedFiles(files);
    setImageError(null);
    
    if (files && files.length > 0) {
      const file = files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target.result;
        // Set preview URL first
        setImagePreviewUrl(dataUrl);
        
        // Validate image dimensions
        validateImageDimensions(dataUrl)
          .then(() => {
            // Get base64 encoded image data only if dimensions are valid
            const base64Image = dataUrl.split(',')[1];
            setImageData(base64Image);
          })
          .catch((error) => {
            console.error("Image validation error:", error.message);
            // Reset image data on error, but keep preview to show the user what's wrong
            setImageData(null);
          });
      };
      reader.readAsDataURL(file);
    } else {
      setImageData(null);
      setImagePreviewUrl(null);
      setImageError(null);
    }
  };

  const handleFileRemove = (event) => {
    setSelectedFiles([]);
    setImageData(null);
    setImagePreviewUrl(null);
    setImageError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Check if image is selected but invalid
    if (imagePreviewUrl && !imageData) {
      return; // Prevent submission if there's an invalid image
    }
    
    setLoading(true);
    
    try {
      await generateVideo(prompt, imageData);
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

  const handleChatSubmit = async (e) => {
    
    e.preventDefault();

    if (chatValue.trim()) {


      const newMsgs = [...chatMessages];
      newMsgs.push({
        role: 'user',
        content: chatValue,
        loading: false
      });
      newMsgs.push({
        role: 'assistant',
        content: "Generating response",
        loading: true
      });

      setChatMessages(newMsgs)

      const res = await chatNova(newMsgs);
      newMsgs[newMsgs.length-1].content = res.message
      newMsgs[newMsgs.length-1].loading = false

      setChatMessages(newMsgs)

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

                  <FormField
                    label="Reference Image (Optional)"
                    description="Upload an image to use as a reference for video generation"
                    stretch
                  >
                    <SpaceBetween size="m">
                      <FileUpload
                        onChange={handleFileChange}
                        onFileRemove={handleFileRemove}
                        value={selectedFiles}
                        i18nStrings={{
                          uploadButtonText: e =>
                            e ? "Choose different file" : "Choose file",
                          dropzoneText: e =>
                            e
                              ? "Drop file to replace"
                              : "Drop file here or select one",
                          removeFileAriaLabel: e => `Remove file ${e}`,
                          limitShowFewer: "Show fewer files",
                          limitShowMore: "Show more files",
                          errorIconAriaLabel: "Error",
                          readButtonText: "View file name",
                          selectedFileLabel: (e, n) => `Selected file: ${e}`,
                          selectedFilesLabel: (e, n) => `Selected files: ${e}`,
                          previewLabel: "Preview image"
                        }}
                        accept="image/*"
                        multiple={false}
                        constraintText="Only image files are supported."
                      />
                      
                      {imagePreviewUrl && (
                        <div style={{ marginTop: '10px' }}>
                          <p>Preview:</p>
                          <img 
                            src={imagePreviewUrl} 
                            alt="Upload preview" 
                            style={{ maxWidth: '100%', maxHeight: '200px', marginTop: '5px' }} 
                          />
                          {imageError && (
                            <Alert
                              type="error"
                              statusIconAriaLabel="Error"
                              header="이미지 해상도 오류"
                              dismissible={false}
                            >
                              {imageError}
                              <div style={{ marginTop: '5px' }}>
                                Image resolution must be 1280x720.
                              </div>
                            </Alert>
                          )}
                        </div>
                      )}
                    </SpaceBetween>
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
                        disabled={(!prompt.trim() && !imageData) || loading || (imagePreviewUrl && !imageData)}
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

                      <h3>Image-to-Video Generation</h3>
                      <ul>
                      <li>Upload a reference image to create videos with similar visual style</li>
                      <li>Use clear, high-quality images for better results</li>
                      <li>Combine with descriptive prompts to guide the video direction</li>
                      <li>The image influences visual style, while the prompt controls content and movement</li>
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
            iconName="gen-ai"
          >
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              height: 'calc(100vh - 120px)', 
              justifyContent: 'space-between' 
            }}>
              <div style={{ overflowY: 'auto' }}>
                {chatMessages.map((message, index) => (
                  <span key={`br-${index}`}>
                  <ChatBubble
                    key={`chat-${index}`}
                    avatar={message.role === 'user' ? <Avatar /> : <Avatar color="gen-ai" initials="AI" loading={message.loading}/>}
                    type='incoming'
                  >
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </ChatBubble>
                  <br />
                  </span>
                ))}
              </div>
              <div style={{ position: 'sticky', bottom: 0, backgroundColor: 'white', paddingTop: '16px' }}>
                <PromptInput
                  onChange={({ detail }) => setChatValue(detail.value)}
                  value={chatValue}
                  onAction={handleChatSubmit}
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