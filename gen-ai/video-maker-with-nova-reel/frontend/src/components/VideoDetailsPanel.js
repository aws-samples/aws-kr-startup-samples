// components/VideoDetailsPanel.js
import React, { useState, useEffect } from 'react';
import Modal from "@cloudscape-design/components/modal";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Spinner from "@cloudscape-design/components/spinner";
import Button from "@cloudscape-design/components/button";
import { fetchVideoDetails } from "../utils/api";

function VideoDetailsPanel({ videoId, visible, onClose }) {
  const [videoDetails, setVideoDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!videoId || !visible) return;
    
    const loadVideoDetails = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const details = await fetchVideoDetails(videoId);
        setVideoDetails(details);
      } catch (err) {
        console.error("Failed to load video details:", err);
        setError("Failed to load video preview. Please try again.");
      } finally {
        setLoading(false);
      }
    };
    
    loadVideoDetails();
  }, [videoId, visible]);

  return (
    <Modal
      visible={visible}
      onDismiss={onClose}
      size="large"
      header={`Video Preview: ${videoId}`}
    >
      <Box padding="l">
        {loading ? (
          <SpaceBetween direction="vertical" size="l" alignItems="center">
            <Spinner size="large" />
            <Box variant="p">Loading video preview...</Box>
          </SpaceBetween>
        ) : error ? (
          <Box variant="h4" color="text-status-error">{error}</Box>
        ) : (
          <SpaceBetween direction="vertical" size="l">
            {videoDetails && videoDetails.presigned_url ? (
              <video controls width="100%" style={{ maxHeight: "60vh" }}>
                <source src={videoDetails.presigned_url} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            ) : (
              <Box variant="h4">No video preview available</Box>
            )}
            
            {videoDetails && (
              <SpaceBetween direction="vertical" size="m">
                <Box variant="h4">Video Details</Box>
                <Box variant="p"><strong>Status:</strong> {videoDetails.status}</Box>
                <Box variant="p"><strong>Created:</strong> {new Date(videoDetails.created_at).toLocaleString()}</Box>
                <Box variant="p"><strong>Updated:</strong> {new Date(videoDetails.updated_at).toLocaleString()}</Box>
                <Box variant="p"><strong>Prompt:</strong> {videoDetails.prompt}</Box>
              </SpaceBetween>
            )}
          </SpaceBetween>
        )}
      </Box>
    </Modal>
  );
}

export default VideoDetailsPanel;