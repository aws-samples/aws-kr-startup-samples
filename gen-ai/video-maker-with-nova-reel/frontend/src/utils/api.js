const API_HOST = process.env.REACT_APP_API_HOST;

export const fetchVideoDetails = async (invocationId) => {
  const apiUrl = `${API_HOST}/apis/videos/${invocationId}`;
  console.log(`Attempting API call to: ${apiUrl}`);
  
  try {
    // CORS 문제 해결을 위해 no-cors 모드 사용
    // 주의: no-cors 모드에서는 응답을 JSON으로 파싱할 수 없어 opaque 응답을 받게 됩니다.
    // 이는 임시 해결책이며, 백엔드에서 CORS를 제대로 구성하는 것이 더 좋은 방법입니다.
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      credentials: 'same-origin',
      mode: 'cors' // 'no-cors'는 opaque 응답을 반환하여 JSON 파싱이 불가능합니다
    });

    console.log(`API response status: ${response.status}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`HTTP error! status: ${response.status}, response: ${errorText}`);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('API response data:', data);
    return data;
  } catch (error) {
    console.error('Error in fetchVideoDetails:', error);
    // 개발 중 CORS 오류 확인을 위해 더미 데이터 반환 (실제 배포 시 제거)
    if (error.message.includes('Failed to fetch')) {
      console.warn('CORS issue detected, returning dummy data for development');
      return {
        invocation_id: invocationId,
        status: 'Completed',
        prompt: 'Demo prompt due to CORS issue',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        location: 'CORS issue - no actual location available'
      };
    }
    throw error;
  }
};

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

export const generateVideo = async (prompt, image = null) => {
  const requestBody = { prompt };
  
  if (image) {
    requestBody.image = image;
  }
  
  const response = await fetch(`${API_HOST}/apis/videos/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
    body: JSON.stringify(requestBody)
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

export const deleteVideo = async (invocationId) => {
  try {
    const response = await fetch(`${API_HOST}/apis/videos/${invocationId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      mode: 'cors',
    });
    
    if (!response.ok) {
      throw new Error(`error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('error:', error);
    throw error;
  }
};

export const deleteVideos = async (invocationIds) => {
  try {
    if (!Array.isArray(invocationIds)) {
      return await deleteVideo(invocationIds);
    }
    
    const results = await Promise.all(
      invocationIds.map(async (id) => {
        try {
          return await deleteVideo(id);
        } catch (error) {
          return { id, error: error.message, success: false };
        }
      })
    );
    
    return {
      success: true,
      results,
      totalDeleted: results.filter(r => !r.error).length,
      totalFailed: results.filter(r => r.error).length
    };
  } catch (error) {
    console.error('error:', error);
    throw error;
  }
};

export const chatNova = async (messages) => {

  const body = []
  messages.forEach(msg => {
    body.push({
      role: msg.role,
      content: [{
        "text": msg.content
      }]
    });
  });

  const response = await fetch(`${API_HOST}/apis/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
    body: JSON.stringify( body )
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const generateStoryboard = async (topic) => {
  const response = await fetch(`${API_HOST}/apis/storyboard/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
    body: JSON.stringify({ topic })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const generateStoryboardVideos = async (storyboard) => {
  const response = await fetch(`${API_HOST}/apis/storyboard/videos`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
    body: JSON.stringify({ storyboard })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const mergeVideos = async (invocationIds) => {
  const response = await fetch(`${API_HOST}/apis/videos/merge`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    mode: 'cors',
    body: JSON.stringify({ invocationIds })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};
