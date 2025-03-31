import * as React from "react";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import Alert from "@cloudscape-design/components/alert";
import Container from "@cloudscape-design/components/container";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Cards from "@cloudscape-design/components/cards";
import Link from "@cloudscape-design/components/link";
import Checkbox from "@cloudscape-design/components/checkbox";
import Modal from "@cloudscape-design/components/modal";
import Table from "@cloudscape-design/components/table";
import { generateStoryboard, generateStoryboardVideos, mergeVideos, fetchVideoDetails, generateVideo } from "../../utils/api";

// Local storage key
const STORYBOARDS_STORAGE_KEY = 'nova-reel-storyboards';

// Video preview modal component
function VideoPreviewModal({ videoId, videoDetails, loading, visible, onClose, onRegenerateVideo }) {
  return (
    <Modal
      visible={visible}
      onDismiss={onClose}
      size="large"
      header={`Scene Video Preview: ${videoId}`}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={onClose}>Close</Button>
            {videoDetails && !loading && (
              <Button 
                variant="primary" 
                onClick={() => onRegenerateVideo(videoId)}
              >
                Regenerate This Scene Video
              </Button>
            )}
          </SpaceBetween>
        </Box>
      }
    >
      <Box padding="l">
        {loading ? (
          <Box textAlign="center">
            <SpaceBetween direction="vertical" size="m">
              <Box variant="h3">Loading video...</Box>
            </SpaceBetween>
          </Box>
        ) : videoDetails && videoDetails.presigned_url ? (
          <SpaceBetween direction="vertical" size="l">
            <video controls width="100%" style={{ maxHeight: "60vh" }}>
              <source src={videoDetails.presigned_url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            
            <SpaceBetween direction="vertical" size="m">
              <Box variant="h4">Video Details</Box>
              <Box variant="p"><strong>Status:</strong> {videoDetails.status}</Box>
              <Box variant="p"><strong>Created:</strong> {new Date(videoDetails.created_at).toLocaleString()}</Box>
              <Box variant="p"><strong>Updated:</strong> {new Date(videoDetails.updated_at).toLocaleString()}</Box>
              <Box variant="p"><strong>Prompt:</strong> {videoDetails.prompt}</Box>
            </SpaceBetween>
          </SpaceBetween>
        ) : (
          <Box variant="h4">Video preview is not available</Box>
        )}
      </Box>
    </Modal>
  );
}

export default function Storyboard() {
  const [topic, setTopic] = React.useState("");
  const [storyboardLoading, setStoryboardLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [success, setSuccess] = React.useState(null);
  const [isGeneratingVideos, setIsGeneratingVideos] = React.useState(false);
  const [isMergingVideos, setIsMergingVideos] = React.useState(false);
  const [mergeModalVisible, setMergeModalVisible] = React.useState(false);
  const [selectedVideos, setSelectedVideos] = React.useState({});
  const [storyboards, setStoryboards] = React.useState([]);
  const [activeStoryboard, setActiveStoryboard] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState("storyboardList");
  
  // States for video preview
  const [selectedVideoId, setSelectedVideoId] = React.useState(null);
  const [selectedSceneIndex, setSelectedSceneIndex] = React.useState(null);
  const [videoModalVisible, setVideoModalVisible] = React.useState(false);
  const [videoDetails, setVideoDetails] = React.useState(null);
  const [videoLoading, setVideoLoading] = React.useState(false);
  const [regeneratingSceneIndex, setRegeneratingSceneIndex] = React.useState(null);
  // 비디오 상태 폴링을 위한 상태 추가
  const [pollingVideoId, setPollingVideoId] = React.useState(null);
  const [pollingInterval, setPollingInterval] = React.useState(null);

  // Load storyboards from local storage
  React.useEffect(() => {
    const savedStoryboards = localStorage.getItem(STORYBOARDS_STORAGE_KEY);
    if (savedStoryboards) {
      try {
        const parsedStoryboards = JSON.parse(savedStoryboards);
        setStoryboards(parsedStoryboards);
      } catch (error) {
        console.error('Error parsing storyboard data:', error);
      }
    }
  }, []);

  // Save storyboards to local storage when updated
  React.useEffect(() => {
    if (storyboards.length > 0) {
      localStorage.setItem(STORYBOARDS_STORAGE_KEY, JSON.stringify(storyboards));
    }
  }, [storyboards]);

  const handleTopicChange = (e) => {
    setTopic(e.detail.value);
  };

  const handleStoryboardGeneration = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setStoryboardLoading(true);
    
    try {
      const result = await generateStoryboard(topic);
      const newStoryboard = {
        id: Date.now().toString(),
        title: topic,
        createdAt: new Date().toISOString(),
        storyboard: result.storyboard,
        videoIds: [],
        videosGenerated: false
      };
      
      const updatedStoryboards = [...storyboards, newStoryboard];
      setStoryboards(updatedStoryboards);
      localStorage.setItem(STORYBOARDS_STORAGE_KEY, JSON.stringify(updatedStoryboards));
      setSuccess("Storyboard has been successfully created.");
      setTopic("");
      setActiveTab("storyboardList");
    } catch (error) {
      console.error("Failed to create storyboard:", error);
      setError("An error occurred while creating the storyboard. Please try again.");
    } finally {
      setStoryboardLoading(false);
    }
  };

  const handleVideoGeneration = async () => {
    if (!activeStoryboard) return;
    
    setError(null);
    setSuccess(null);
    setIsGeneratingVideos(true);
    
    try {
      const result = await generateStoryboardVideos(activeStoryboard.storyboard);
      const videoIds = result.invocationIds;
      
      // Update the current storyboard with video IDs
      const updatedStoryboards = storyboards.map(sb => 
        sb.id === activeStoryboard.id 
          ? { ...sb, videoIds, videosGenerated: true } 
          : sb
      );
      
      setStoryboards(updatedStoryboards);
      localStorage.setItem(STORYBOARDS_STORAGE_KEY, JSON.stringify(updatedStoryboards));
      
      setActiveStoryboard(prev => ({ ...prev, videoIds, videosGenerated: true }));
      setSuccess("Video generation request has been successfully submitted. You can check them in the Outputs page after completion.");
    } catch (error) {
      console.error("Failed to generate videos:", error);
      setError("An error occurred while generating videos. Please try again.");
    } finally {
      setIsGeneratingVideos(false);
    }
  };

  const handleMergeModalOpen = () => {
    if (!activeStoryboard || !activeStoryboard.videoIds || activeStoryboard.videoIds.length < 2) {
      setError("Not enough videos to merge. You need at least 2 videos.");
      return;
    }
    
    // Initialize selection state (select all videos by default)
    const initialSelection = {};
    activeStoryboard.videoIds.forEach((id, index) => {
      initialSelection[index] = true;
    });
    
    setSelectedVideos(initialSelection);
    setMergeModalVisible(true);
  };

  const handleMergeModalClose = () => {
    setMergeModalVisible(false);
  };

  const handleVideoSelection = (index, checked) => {
    setSelectedVideos(prev => ({
      ...prev,
      [index]: checked
    }));
  };

  const handleMergeVideos = async () => {
    if (!activeStoryboard) return;
    
    setIsMergingVideos(true);
    setError(null);
    
    try {
      // Create a list of selected video IDs
      const selectedVideoIds = Object.keys(selectedVideos)
        .filter(index => selectedVideos[index])
        .map(index => activeStoryboard.videoIds[index]);
      
      if (selectedVideoIds.length < 2) {
        setError("You must select at least 2 videos.");
        setIsMergingVideos(false);
        return;
      }
      
      // Merge request
      await mergeVideos(selectedVideoIds);
      setSuccess("Video merge request has been successfully submitted. You can check it in the Outputs page after completion.");
      setMergeModalVisible(false);
    } catch (error) {
      console.error("Failed to merge videos:", error);
      setError("An error occurred while merging videos. Please try again.");
    } finally {
      setIsMergingVideos(false);
    }
  };

  const handleStoryboardSelect = (storyboard) => {
    setActiveStoryboard(storyboard);
    setActiveTab("storyboardDetail");
  };

  const handleBackToList = () => {
    setActiveStoryboard(null);
    setActiveTab("storyboardList");
  };

  const handleDeleteStoryboard = (storyboardId) => {
    const updatedStoryboards = storyboards.filter(sb => sb.id !== storyboardId);
    setStoryboards(updatedStoryboards);
    localStorage.setItem(STORYBOARDS_STORAGE_KEY, JSON.stringify(updatedStoryboards));
    
    if (activeStoryboard && activeStoryboard.id === storyboardId) {
      setActiveStoryboard(null);
      setActiveTab("storyboardList");
    }
    
    setSuccess("Storyboard has been deleted.");
  };

  // 비디오 상태를 확인하는 폴링 함수 추가
  const startPollingVideoStatus = React.useCallback((videoId, sceneIndex) => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    setPollingVideoId(videoId);
    
    const interval = setInterval(async () => {
      try {
        const details = await fetchVideoDetails(videoId);
        if (details && details.status === 'Completed') {
          // 폴링 중지 및 상태 업데이트
          clearInterval(interval);
          setPollingInterval(null);
          setPollingVideoId(null);
          
          // 비디오 상세 정보 업데이트
          setVideoDetails(details);
          
          // 성공 메시지 표시
          setSuccess(`Scene ${sceneIndex + 1} video has been successfully generated!`);
        }
      } catch (error) {
        console.error('Error polling video status:', error);
      }
    }, 5000); // 5초마다 폴링
    
    setPollingInterval(interval);
  }, [pollingInterval]);

  // 비디오 폴링 중지 함수
  const stopPollingVideoStatus = React.useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
      setPollingVideoId(null);
    }
  }, [pollingInterval]);

  // 컴포넌트 언마운트 시 폴링 중지
  React.useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // 비디오 미리보기 함수 수정
  const handleVideoPreview = async (videoId, sceneIndex) => {
    if (!videoId) return;
    
    setSelectedVideoId(videoId);
    setSelectedSceneIndex(sceneIndex);
    setVideoModalVisible(true);
    setVideoLoading(true);
    
    try {
      const details = await fetchVideoDetails(videoId);
      setVideoDetails(details);
      
      // 비디오가 아직 생성 중이면 폴링 시작
      if (details && details.status !== 'Completed') {
        startPollingVideoStatus(videoId, sceneIndex);
      }
    } catch (error) {
      console.error("Failed to load video details:", error);
      setError("An error occurred while loading video details.");
    } finally {
      setVideoLoading(false);
    }
  };
  
  // 모달 닫기 함수 수정
  const handleCloseVideoModal = () => {
    setVideoModalVisible(false);
    setSelectedVideoId(null);
    setSelectedSceneIndex(null);
    setVideoDetails(null);
    stopPollingVideoStatus(); // 모달 닫을 때 폴링 중지
  };
  
  // 비디오 재생성 함수 수정
  const handleRegenerateSceneVideo = async (videoId) => {
    if (!activeStoryboard || selectedSceneIndex === null) return;
    
    setError(null);
    setSuccess(null);
    setRegeneratingSceneIndex(selectedSceneIndex);
    setVideoModalVisible(false);
    stopPollingVideoStatus(); // 기존 폴링 중지
    
    try {
      const scene = activeStoryboard.storyboard.scenes[selectedSceneIndex];
      const result = await generateVideo(scene.prompt);
      const newVideoId = result.invocationId;
      
      // Update video IDs array for the current storyboard
      const updatedVideoIds = [...activeStoryboard.videoIds];
      updatedVideoIds[selectedSceneIndex] = newVideoId;
      
      // Update storyboard with videosGenerated flag set to true
      const updatedStoryboards = storyboards.map(sb => 
        sb.id === activeStoryboard.id 
          ? { ...sb, videoIds: updatedVideoIds, videosGenerated: true } 
          : sb
      );
      
      setStoryboards(updatedStoryboards);
      localStorage.setItem(STORYBOARDS_STORAGE_KEY, JSON.stringify(updatedStoryboards));
      
      setActiveStoryboard(prevState => ({
        ...prevState,
        videoIds: updatedVideoIds,
        videosGenerated: true
      }));
      
      setSuccess(`Scene ${selectedSceneIndex + 1} video regeneration has been requested. You can check it in the preview after completion.`);
      
      // 새로운 비디오 상태 폴링 시작
      startPollingVideoStatus(newVideoId, selectedSceneIndex);
    } catch (error) {
      console.error("Failed to regenerate scene video:", error);
      setError("An error occurred while regenerating the scene video. Please try again.");
    } finally {
      setRegeneratingSceneIndex(null);
    }
  };

  const renderStoryboardItems = () => {
    if (!activeStoryboard || !activeStoryboard.storyboard || !activeStoryboard.storyboard.scenes || !activeStoryboard.storyboard.scenes.length) {
      return null;
    }

    return (
      <SpaceBetween size="l">
        <Cards
          cardDefinition={{
            header: item => (
              <Header variant="h3">{`Scene ${item.index + 1}`}</Header>
            ),
            sections: [
              {
                id: "description",
                header: "Description",
                content: item => item.description
              },
              {
                id: "prompt",
                header: "Prompt",
                content: item => (
                  <ExpandableSection headerText="View Video Generation Prompt">
                    <Box color="text-status-info">{item.prompt}</Box>
                  </ExpandableSection>
                )
              },
              {
                id: "video",
                header: "Video",
                content: item => (
                  activeStoryboard.videoIds && activeStoryboard.videoIds[item.index] ? (
                    <Box>
                      <Button
                        onClick={() => handleVideoPreview(activeStoryboard.videoIds[item.index], item.index)}
                        loading={regeneratingSceneIndex === item.index || (pollingVideoId === activeStoryboard.videoIds[item.index])}
                        disabled={regeneratingSceneIndex === item.index}
                      >
                        {pollingVideoId === activeStoryboard.videoIds[item.index] ? "Generating..." : "Video Preview"}
                      </Button>
                    </Box>
                  ) : (
                    <Box>Video not yet generated</Box>
                  )
                )
              }
            ]
          }}
          cardsPerRow={[
            { cards: 1 },
            { minWidth: 500, cards: 2 }
          ]}
          items={activeStoryboard.storyboard.scenes.map((scene, index) => ({
            ...scene,
            index
          }))}
          trackBy="index"
          empty={
            <Box textAlign="center" color="inherit">
              <b>No storyboard available</b>
              <Box padding={{ bottom: "s" }} variant="p" color="inherit">
                Enter a topic above and click the Create Storyboard button.
              </Box>
            </Box>
          }
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    onClick={handleVideoGeneration}
                    disabled={!activeStoryboard || isGeneratingVideos}
                    loading={isGeneratingVideos}
                  >
                    Generate Videos
                  </Button>
                  {activeStoryboard && activeStoryboard.videosGenerated && activeStoryboard.videoIds.length >= 2 && (
                    <Button 
                      onClick={handleMergeModalOpen}
                      disabled={isMergingVideos}
                    >
                      Merge Videos
                    </Button>
                  )}
                  <Button onClick={handleBackToList}>
                    Back to List
                  </Button>
                </SpaceBetween>
              }
            >
              {activeStoryboard ? `Storyboard: ${activeStoryboard.title}` : 'Storyboard'}
            </Header>
          }
        />
      </SpaceBetween>
    );
  };

  const renderStoryboardList = () => {
    return (
      <Container
        header={
          <Header
            variant="h2"
            actions={
              <Button
                variant="primary"
                onClick={() => {
                  setActiveTab("createStoryboard");
                }}
              >
                Create Storyboard
              </Button>
            }
          >
            Storyboard List
          </Header>
        }
      >
        <Table
          items={storyboards}
          columnDefinitions={[
            {
              id: "title",
              header: "Title",
              cell: item => (
                <Link
                  href="#"
                  onFollow={e => {
                    e.preventDefault();
                    handleStoryboardSelect(item);
                  }}
                >
                  {item.title}
                </Link>
              )
            },
            {
              id: "createdAt",
              header: "Created Date",
              cell: item => new Date(item.createdAt).toLocaleString()
            },
            {
              id: "status",
              header: "Status",
              cell: item => item.videosGenerated ? "Videos Generated" : "Storyboard Only"
            },
            {
              id: "actions",
              header: "Actions",
              cell: item => (
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    onClick={() => handleStoryboardSelect(item)}
                  >
                    View Details
                  </Button>
                  <Button
                    variant="normal"
                    onClick={() => handleDeleteStoryboard(item.id)}
                  >
                    Delete
                  </Button>
                </SpaceBetween>
              )
            }
          ]}
          empty={
            <Box textAlign="center" color="inherit">
              <b>No storyboards found</b>
              <Box padding={{ bottom: "s" }} variant="p" color="inherit">
                Click the Create Storyboard button to create a new storyboard.
              </Box>
            </Box>
          }
        />
      </Container>
    );
  };

  const renderCreateStoryboardForm = () => {
    return (
      <Container
        header={
          <Header variant="h2">Create Storyboard</Header>
        }
      >
        <form onSubmit={handleStoryboardGeneration}>
          <SpaceBetween size="l">
            <FormField
              label="Topic"
              description="Enter a topic for your storyboard (e.g., summer, adventure, space voyage)"
              constraintText="Keep your topic concise and clear."
            >
              <Input
                value={topic}
                onChange={handleTopicChange}
                placeholder="summer"
              />
            </FormField>
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  onClick={() => setActiveTab("storyboardList")}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  type="submit"
                  loading={storyboardLoading}
                  disabled={!topic.trim() || storyboardLoading}
                >
                  Create Storyboard
                </Button>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </form>
      </Container>
    );
  };

  const renderContent = () => {
    switch (activeTab) {
      case "storyboardList":
        return renderStoryboardList();
      case "storyboardDetail":
        return renderStoryboardItems();
      case "createStoryboard":
        return renderCreateStoryboardForm();
      default:
        return renderStoryboardList();
    }
  };

  return (
    <Box margin={{ bottom: "l" }}>
      <SpaceBetween size="l">
        <Header variant="h1">Storyboard</Header>
        
        {error && (
          <Alert
            dismissible
            onDismiss={() => setError(null)}
            type="error"
          >
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert
            dismissible
            onDismiss={() => setSuccess(null)}
            type="success"
          >
            {success}
          </Alert>
        )}
        
        {renderContent()}
        
        <Modal
          visible={mergeModalVisible}
          onDismiss={handleMergeModalClose}
          header="Merge Videos"
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={handleMergeModalClose}>Cancel</Button>
                <Button
                  variant="primary"
                  onClick={handleMergeVideos}
                  loading={isMergingVideos}
                  disabled={
                    isMergingVideos ||
                    Object.values(selectedVideos).filter(Boolean).length < 2
                  }
                >
                  Merge
                </Button>
              </SpaceBetween>
            </Box>
          }
        >
          <SpaceBetween size="m">
            <Box variant="p">
              Select videos to merge. You need to select at least 2 videos.
            </Box>
            {activeStoryboard && activeStoryboard.videoIds && activeStoryboard.videoIds.map((id, index) => (
              <Checkbox
                key={index}
                checked={selectedVideos[index] || false}
                onChange={({ detail }) => handleVideoSelection(index, detail.checked)}
              >
                {`Video ${index + 1}`}
              </Checkbox>
            ))}
          </SpaceBetween>
        </Modal>
        
        {/* Video preview modal */}
        <VideoPreviewModal
          videoId={selectedVideoId}
          videoDetails={videoDetails}
          loading={videoLoading}
          visible={videoModalVisible}
          onClose={handleCloseVideoModal}
          onRegenerateVideo={handleRegenerateSceneVideo}
        />
      </SpaceBetween>
    </Box>
  );
} 