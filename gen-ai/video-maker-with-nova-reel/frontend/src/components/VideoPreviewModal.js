// components/VideoPreviewModal.js
import React from 'react';
import Modal from "@cloudscape-design/components/modal";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";

function VideoPreviewModal({ videoId, videoDetails, loading, visible, onClose }) {
  return (
    <Modal
      visible={visible}
      onDismiss={onClose}
      size="large"
      header={`Video Preview: ${videoId}`}
    >
      <Box padding="l">
        {loading ? (
          <Box textAlign="center">
            <SpaceBetween direction="vertical" size="m">
              <Box variant="h3">Loading video preview...</Box>
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
          <Box variant="h4">No video preview available</Box>
        )}
      </Box>
    </Modal>
  );
}

export default VideoPreviewModal;