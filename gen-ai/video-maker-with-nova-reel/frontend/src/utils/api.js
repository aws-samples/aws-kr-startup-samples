const API_HOST = process.env.REACT_APP_API_HOST;

export const fetchVideos = async (limit, nextToken) => {
  let url = `${API_HOST}/apis/videos?limit=${limit}&sort=created_at&order=desc`;
  if (nextToken) {
    url += `&nextToken=${nextToken}`;
  }
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const generateVideo = async (prompt) => {
  const response = await fetch(`${API_HOST}/apis/videos/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
    body: JSON.stringify({ prompt })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const downloadVideo = async (invocationId) => {
  const response = await fetch(`${API_HOST}/apis/videos/${invocationId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors'
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  const presignedUrl = data.presigned_url;
  
  if (!presignedUrl) {
    throw new Error('No presigned URL found in response');
  }

  // Create a temporary link element and trigger download
  const a = document.createElement('a');
  a.href = presignedUrl;
  a.download = `video-${invocationId}.mp4`;
  document.body.appendChild(a);
  a.click();
  a.remove();
};

// ... other API functions 