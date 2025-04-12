import * as React from "react";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import FormField from "@cloudscape-design/components/form-field";
import Textarea from "@cloudscape-design/components/textarea";
import Alert from "@cloudscape-design/components/alert";
import Select from "@cloudscape-design/components/select";
import Input from "@cloudscape-design/components/input";
import Container from "@cloudscape-design/components/container";
import AppLayout from "@cloudscape-design/components/app-layout";
import ProgressBar from "@cloudscape-design/components/progress-bar";
import Slider from "@cloudscape-design/components/slider";
import Cards from "@cloudscape-design/components/cards";

export default function ImageGenerateForm() {
  const [prompt, setPrompt] = React.useState("");
  const [negativePrompt, setNegativePrompt] = React.useState("");
  const [aspectRatio, setAspectRatio] = React.useState({ label: "1280 x 720 (9:16)", value: "1280x720" });
  const [imageCount, setImageCount] = React.useState(1);
  const [isLoading, setIsLoading] = React.useState(false);
  const [showSuccess, setShowSuccess] = React.useState(false);
  const [selectedImages, setSelectedImages] = React.useState([]);
  const [generatedImages, setGeneratedImages] = React.useState([]);
  const [error, setError] = React.useState(null);
  const [promptError, setPromptError] = React.useState(null);

  const aspectRatioOptions = [
    { label: "1280 x 720 (16:9)", value: "landscape" },
    { label: "720 x 1280 (9:16)", value: "portrait" }
  ];

  const validatePrompt = (text) => {
    if (!text.trim()) {
      return 'Prompt는 필수 입력 항목입니다.';
    }
    if (text.length < 1 || text.length > 1024) {
      return 'Prompt는 1-1024자 사이여야 합니다.';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setShowSuccess(false);
    setPromptError(null);

    const promptValidationError = validatePrompt(prompt);
    if (promptValidationError) {
      setPromptError(promptValidationError);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${process.env.REACT_APP_API_HOST}/apis/images/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          negative_prompt: negativePrompt,
          height: aspectRatio.value === 'landscape' ? 720 : 1280,
          width: aspectRatio.value === 'landscape' ? 1280 : 720,
          number_of_images: imageCount
        })
      });

      if (!response.ok) {
        throw new Error('이미지 생성에 실패했습니다.');
      }

      const data = await response.json();
      const newImages = data.images.map((image, index) => ({
        id: `image-${Date.now()}-${index}`,
        imageUrl: image.url,
        prompt: prompt,
        negativePrompt: negativePrompt,
        aspectRatio: aspectRatio.value,
        createdAt: new Date().toISOString()
      }));
      setGeneratedImages(prevImages => [...prevImages, ...newImages]);
      setShowSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      for (const image of selectedImages) {
        const response = await fetch(image.imageUrl);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `generated-image-${image.id}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Failed to download images:', error);
    }
  };

  return (
    <ContentLayout
      defaultPadding
      header={
        <SpaceBetween size="m">
          <Header
            variant="h1"
          >
            Image Playground
          </Header>
        </SpaceBetween>
      }
    >
      <Container>
        <AppLayout
          navigationWidth={320}
          toolsHide
          navigation={
            <SpaceBetween size="l" className="custom-nav">
              <style>
                {`
                  .custom-nav {
                    padding: 0 16px 0 0;
                  }
                `}
              </style>
              <Header
                variant="h2"
                divider
              >
                Configurations
              </Header>
              <FormField
                label="Action"
              >
                <Select
                  selectedOption={{ label: "Generate image", value: "generate" }}
                  options={[{ label: "Generate image", value: "generate" }]}
                  disabled
                />
              </FormField>

              <FormField
                label="Negative prompt"
              >
                <Textarea
                  value={negativePrompt}
                  onChange={({ detail }) => setNegativePrompt(detail.value)}
                  placeholder="Enter what you don't want to see..."
                />
              </FormField>

              <FormField
                label="Size (px) / Aspect ratio"
              >
                <Select
                  selectedOption={aspectRatio}
                  onChange={({ detail }) => setAspectRatio(detail.selectedOption)}
                  options={aspectRatioOptions}
                />
              </FormField>

              <FormField
                label="Number of images"
                description="Slide to select number of images (1-5)"
              >
                <div style={{ padding: '0 12px' }}>
                  <Slider
                    value={imageCount}
                    onChange={({ detail }) => setImageCount(detail.value)}
                    min={1}
                    max={5}
                    step={1}
                    marks={[
                      { value: 1, label: "1" },
                      { value: 2, label: "2" },
                      { value: 3, label: "3" },
                      { value: 4, label: "4" },
                      { value: 5, label: "5" }
                    ]}
                  />
                </div>
              </FormField>
            </SpaceBetween>
          }
          content={
            <form onSubmit={handleSubmit}>
              <SpaceBetween size="l">
                <Header
                  variant="h2"
                  divider
                >
                  Image Generation
                </Header>
                {showSuccess && (
                  <Alert
                    dismissible
                    onDismiss={() => setShowSuccess(false)}
                    type="success"
                  >
                    Image generation request has been successfully submitted.
                  </Alert>
                )}
                <FormField
                  label="Prompt"
                  description="Enter a description of the image you want to generate"
                  errorText={promptError}
                  stretch={true}
                >
                  <Textarea
                    value={prompt}
                    onChange={({ detail }) => {
                      setPrompt(detail.value);
                      setPromptError(validatePrompt(detail.value));
                    }}
                    placeholder="A beautiful landscape with mountains and a lake..."
                    rows={6}
                    style={{ width: '100%', maxWidth: '100%' }}
                  />
                </FormField>

                <Box float="right">
                  <Button
                    variant="primary"
                    type="submit"
                    loading={isLoading}
                    disabled={!prompt.trim() || isLoading || promptError}
                  >
                    Generate
                  </Button>
                </Box>

                <div style={{ 
                  maxHeight: '600px', 
                  overflowY: 'auto',
                  padding: '16px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  marginBottom: '16px'
                }}>
                  <SpaceBetween size="l">
                    <Cards
                      onSelectionChange={({ detail }) => setSelectedImages(detail.selectedItems)}
                      selectedItems={selectedImages}
                      ariaLabels={{
                        itemSelectionLabel: (e, n) => `select image ${n.id}`,
                        selectionGroupLabel: "Image selection"
                      }}
                      cardDefinition={{
                        sections: [
                          {
                            id: "image",
                            content: item => (
                              <div style={{ 
                                width: '100%', 
                                height: '250px', 
                                overflow: 'hidden',
                                position: 'relative',
                                backgroundColor: '#f5f5f5'
                              }}>
                                <img
                                  style={{ 
                                    position: 'absolute',
                                    top: '50%',
                                    left: '50%',
                                    transform: 'translate(-50%, -50%)',
                                    width: item.aspectRatio === 'landscape' ? '100%' : 'auto',
                                    height: item.aspectRatio === 'landscape' ? '100%' : '100%',
                                    objectFit: item.aspectRatio === 'landscape' ? 'cover' : 'contain'
                                  }}
                                  src={item.imageUrl}
                                  alt="Generated image"
                                />
                                <div style={{ 
                                  position: 'absolute',
                                  bottom: 0,
                                  left: 0,
                                  right: 0,
                                  padding: '4px 8px',
                                  backgroundColor: 'rgba(0, 0, 0, 0.6)',
                                  color: 'white',
                                  fontSize: '10px',
                                  lineHeight: '1.2'
                                }}>
                                  <div style={{ marginBottom: '2px' }}>prompt: {item.prompt}</div>
                                  {item.negativePrompt && <div style={{ marginBottom: '2px' }}>negative: {item.negativePrompt}</div>}
                                </div>
                              </div>
                            )
                          }
                        ]
                      }}
                      cardsPerRow={[
                        { cards: 1 },
                        { minWidth: 500, cards: 2 },
                        { minWidth: 900, cards: 3 }
                      ]}
                      items={generatedImages}
                      loadingText="Loading images"
                      selectionType="multi"
                      trackBy="id"
                      empty={
                        <Box textAlign="center" color="inherit">
                          <SpaceBetween size="m">
                            <b>No images generated yet</b>
                          </SpaceBetween>
                        </Box>
                      }
                    />
                  </SpaceBetween>
                </div>

                {generatedImages.length > 0 && (
                  <Box float="right">
                    <Button
                      onClick={handleDownload}
                      disabled={selectedImages.length === 0}
                      iconName="download"
                    >
                      Download selected ({selectedImages.length})
                    </Button>
                  </Box>
                )}
              </SpaceBetween>
            </form>
          }
        />
      </Container>
    </ContentLayout>
  );
} 