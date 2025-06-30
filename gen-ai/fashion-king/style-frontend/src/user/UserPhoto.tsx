import React, { useRef, useState, useEffect } from 'react';
import Webcam from 'react-webcam';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation, Trans } from 'react-i18next';
import {Buffer} from 'buffer';
import axios from 'axios';
import './UserPhoto.css';
import { sendGenerateImageCommand, sendUserAgreementCommand, uuidX } from './apiUtils';
import PrivacyModal from './PrivacyModal';

const historical_periods = [
  "ancient_rome",
  // "medieval_period",
  // "renaissance",
  // "belle_epoque",
  // "roaring_twenties"
];

const getRandomHistoricalPeriod = () => {
  const randomIndex = Math.floor(Math.random() * historical_periods.length);
  return historical_periods[randomIndex];
};

const UserPhoto = ({ signOut, user }) => {
  const webcamRef = useRef(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [uploadProgress1, setUploadProgress1] = useState(0); 
  const [uploadProgress2, setUploadProgress2] = useState(100); 
  const navigate = useNavigate();
  const [showPrivacyModal, setShowPrivacyModal] = useState(true);
  const [agreementUserName, setAgreementUserName] = useState(null);
  const [agreementResult, setAgreementResult] = useState(false);
  const { t } = useTranslation();

  const location = useLocation();
  let { gender, skinTone, readyToTravel } = location.state;
  
  useEffect(() => {
    setShowPrivacyModal(true);
  }, []);

  const handlePrivacyModalClose = () => {
    setShowPrivacyModal(false);
    navigate('/');
  };

  const handlePrivacyModalAgree = (name) => {
    console.log("handlePrivacyModal-Agree");
    setAgreementResult(true);
    setAgreementUserName(name);
    setShowPrivacyModal(false);
  };

  const handlePrivacyModalDisagree = () => {
    console.log("handlePrivacyModal-Disagree");
    setShowPrivacyModal(false);
    setAgreementResult(false);
    navigate('/'); 
  };

  const capture = () => {
    if(webcamRef.current){
        const imageSrc = webcamRef.current.getScreenshot();
        console.log("img src= "+imageSrc);
        setCapturedImage(imageSrc);
    }
  };

  const uploadImage = () => {
    const uuid = uuidX(user.username);
    setUploadProgress1(1);
    const requestBody = {
      userId: user.username,
      theme: getRandomHistoricalPeriod(),
      gender: gender === 'M' ? 'male' : 'female',
      skin: skinTone
    };

    fetch(process.env.REACT_APP_API_ENDPOINT+`/images/upload`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })
      .then(response => response.json())
      .then(data => {
        console.log('Fetched presigned data:', data);
        console.log('Fetched presigned url:', data.uploadUrl); 
        console.log('uploading Image To S3');
        uploadImageToS3(data.uploadUrl, capturedImage).then(() => setUploadProgress2(50));
        console.log('call Agreement API');
        console.log(data)
        sendUserAgreementCommand(data.uploadUrl, user.username, agreementUserName);
        setUploadProgress2(100);
        navigate('/user/finish');
    })
    .catch(error => console.error('Error while uploading the image:', error));
  }

  const uploadImageToS3 = async (presignedUrl4Put: string, imageSrc: any) => {
    if (presignedUrl4Put) {
      try {
        // Data URI 형식에서 Blob으로 변환
        const response = await fetch(imageSrc);
        const blob = await response.blob();
        
        const config = {
          onUploadProgress: (progressEvent: any) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress1(percentCompleted);
          },
        };

        // Content-Type 헤더 설정
        const header = {
          'Content-Type': 'image/jpeg',
        };

        console.log("Uploading to:", presignedUrl4Put);
        // Blob 형식으로 업로드
        const uploadResponse = await axios.put(presignedUrl4Put, blob, {
          ...config,
          headers: header
        });

        console.log("Upload response:", uploadResponse);
        
        if (uploadResponse.status === 200) {
          setUploadProgress1(100);
          console.log('Image uploaded successfully');
        } else {
          console.error('Error uploading image with status:', uploadResponse.status);
        }
      } catch (error) {
        console.error('Error details:', error.response ? error.response.data : error.message);
        console.error('Error uploading image:', error);
      }
    } else {
      console.error('Presigned URL not available');
    }
  };

  const navigateToStart = () => {
    navigate('/');
  };

  const navigateToTake = () => {
    setCapturedImage(null);
    navigate('/user/photo', {
      state: { gender, skinTone, readyToTravel },
    });
  };

  return (
    <div className="container">
      <PrivacyModal
        isOpen={showPrivacyModal}
        onClose={handlePrivacyModalClose}
        onAgree={handlePrivacyModalAgree}
        onDisagree={handlePrivacyModalDisagree}
      
      />
      <div className="webcam-container">
      {(() => {
        if (!capturedImage) {
          return (<div className="webcam-container">
            <Webcam
              audio={false}
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              videoConstraints={{
                facingMode: 'user'
              }}
            />
          </div>);
        } else {
          return (<div className="webcam-container">
            <img src={capturedImage} alt="Captured Image" />
          </div>);
        }
      })()}
      </div>
      <div>
        {Math.min(uploadProgress1, uploadProgress2) > 0 && (
          <div>
            <progress value={Math.min(uploadProgress1, uploadProgress2)} max="100" />
            <span>{Math.min(uploadProgress1, uploadProgress2)}%</span>
          </div>
        )}
      </div>
      {(() => {
        if (!capturedImage) {
          return (
            <div className="capture-button"><br/><button onClick={capture}>{t('takePhoto')}</button></div>
          );
        } else {
          if (Math.min(uploadProgress1, uploadProgress2) === 100) {
            return (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div className="upload-completed-message" style={{ textAlign: 'center' }}><Trans i18nKey="uploadComplete"/></div>
                <br />
                <div className="capture-button" >
                  <button onClick={navigateToStart}>{t('goBackToStart')}</button>
                </div>
              </div>
            );
          } else {
            return (
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 17 }}>
                <div className="retake-button">
                  <button onClick={navigateToTake} disabled={Math.min(uploadProgress1, uploadProgress2) > 0 && Math.min(uploadProgress1, uploadProgress2) < 100}>{t('retake')}</button>
                </div>
                <div className="capture-button"  style={{ marginLeft: '12px' }}>
                  <button onClick={uploadImage} disabled={Math.min(uploadProgress1, uploadProgress2) > 0 && Math.min(uploadProgress1, uploadProgress2) < 100}>{t('upload')}</button>
                </div>
              </div>
            );
          }
        }
      })()}
    </div>
  );
};

export default UserPhoto;
