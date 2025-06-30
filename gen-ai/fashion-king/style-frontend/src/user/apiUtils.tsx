import axios from 'axios';

export const uuidX = (username) => {
  return `${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${new Date().toISOString().slice(11, 19).replace(/:/g, "")}-${username}`;
}

export const sendGenerateImageCommand = async (uuid, gender, skinTone, useSelfie) => {
  try {
    console.log("sendGenerateImageCommand for "+uuid);
    const response = await axios.post(
      `${process.env.REACT_APP_API_ENDPOINT}/images/${uuid}/generate`,
      { gender, skintone: skinTone, useSelfie: useSelfie }
    );

    if (response.status === 200) {
      console.log('response for the generate request:', response.data);
      return response.status;
    } else {
      throw new Error('Failed to generate image.');
    }
  } catch (error) {
    console.error('Error in sendGenerateImageCommand:', error);
    throw error;
  }
};

export const sendUserAgreementCommand = async (presignedUrl4Put, username, agreementUserName) => {
  try {
    const regex = /face-image\/(.+?)\?/;
    const match = presignedUrl4Put.match(regex);

    const requestedAt = new Date().toISOString();
    let id = `${requestedAt}-${username}`;
    if (match) {
      id = match[1];
    }

    const postData = {
      id,
      name: agreementUserName,
      agree: 'Y',
      userId: username,
      savedAt: requestedAt,
    };

    console.log("postData= "+JSON.stringify(postData));

    const config = {
      headers: {
        'Content-Type': 'application/json',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      },
    };

    const response = await axios.post(
      `${process.env.REACT_APP_USER_AGREEMENT_ENDPOINT}/agree`, postData, config);

    if (response.status === 200) {
      console.log('Agreement updated successfully');
    } else {
      console.error('Error updating agreement');
    }
  } catch (error) {
    console.error('Error calling Agreement API:', error);
    throw error;
  }
};