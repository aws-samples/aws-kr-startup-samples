import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './UserAsking.css';
import backgroundImage from '../assets/bg-2.png';
import { sendGenerateImageCommand, uuidX } from './apiUtils';

type Gender = 'M' | 'F' | 'NS' | null;
type SkinTone = 'light_pale_white' | 'white_fair' | 'medium_white_to_olive' | 'olive_tone' | 'light_brown' | 'dark_brown' | null;

const UserAsking = ({ signOut, user }) => {
  const [showSecondPanel, setShowSecondPanel] = useState(true);
  const [showThirdPanel, setShowThirdPanel] = useState(true);
  const [gender, setGender] = useState<Gender>('F');
  const [skinTone, setSkinTone] = useState<SkinTone>('medium_white_to_olive');
  const [useSelfie, setUseSelfie] = useState<boolean | null>(false);
  const [yesSelected, setYesSelected] = useState(true);
  const [noSelected, setNoSelected] = useState(false);
  const navigate = useNavigate();

  // Refs for thirdPanel and travel-button
  const thirdPanelRef = useRef<HTMLDivElement | null>(null);
  const travelButtonRef = useRef<HTMLButtonElement | null>(null);

  const resetSelections = () => {
    setShowSecondPanel(false);
    setShowThirdPanel(false);
    setGender(null);
    setSkinTone(null);
    setUseSelfie(null);
  };

  const handleYesClick = () => {
    resetSelections();
    setYesSelected(true);
    setNoSelected(false);
    setShowSecondPanel(true);
  };

  const handleNoClick = () => {
    resetSelections();
    setYesSelected(false);
    setNoSelected(true);
    setShowThirdPanel(true);
  };

  const handleSkinToneSelect = (tone: SkinTone) => {
    setSkinTone(tone);
    if (gender !== null) {
      setShowThirdPanel(true);
    }
  };

  const handleGenderSelect = (gender: Gender) => {
    setGender(gender);
    if (skinTone !== null) {
      setShowThirdPanel(true);
    }
  };

  const handleTravel = () => {
    if(useSelfie) {
      navigate('/user/photo', {
        state: { gender, skinTone, readyToTravel: useSelfie },
      });
    } else {
      //sendGenerateImageCommand(uuidX(user.username), gender, skinTone, useSelfie);
      navigate('/user/finish');
    }
  };

  // Scroll effect when panels or buttons appear
  useEffect(() => {
    if (showThirdPanel && thirdPanelRef.current) {
      thirdPanelRef.current.scrollIntoView({ behavior: 'smooth' });
    } else if (useSelfie !== null && travelButtonRef.current) {
      travelButtonRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [showThirdPanel, useSelfie]);

  return (
    <div className="user-asking" style={{ backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url(${backgroundImage})` }}>
      <div className="panel">
        <p className="panel-text"><b>We will show you an image of your past self.</b></p>
        <p className="panel-text">You can choose your gender and skin tone based on your preference.<br/>Would you like to choose?</p>
        <div className="buttons">
          <button
            className={`option-button ${yesSelected ? 'selected' : ''}`}
            onClick={handleYesClick}
          >
            Manual Select
          </button>
          <button
            className={`option-button ${noSelected ? 'selected' : ''}`}
            onClick={handleNoClick}
          >
            Auto Select
          </button>
        </div>
      </div>

      {showSecondPanel && (
        <div className="panel">
          <p className="panel-text">Tell us about the past self you remember.</p>
          <div className="question">
            <label className="question-label">What was your gender?</label>
            <div className="buttons">
              <button
                className={`option-button ${gender === 'M' ? 'selected' : ''}`}
                onClick={() => handleGenderSelect('M')}
              >
                Male
              </button>
              <button
                className={`option-button ${gender === 'F' ? 'selected' : ''}`}
                onClick={() => handleGenderSelect('F')}
              >
                Female
              </button>
              <button
                className={`option-button ${gender === 'NS' ? 'selected' : ''}`}
                onClick={() => handleGenderSelect('NS')}
              >
                Non-specific
              </button>
            </div>
          </div>
          <div className="question">
            <label className="question-label">What was your skin tone?</label>
            <div className="buttons">
              <button
                className={`skin-button ${skinTone === 'light_pale_white' ? 'selected' : ''}`}
                onClick={() => handleSkinToneSelect('light_pale_white')}
                style={{ backgroundColor: '#F6D1AF' }}
              />
              <button
                className={`skin-button ${skinTone === 'white_fair' ? 'selected' : ''}`}
                onClick={() => handleSkinToneSelect('white_fair')}
                style={{ backgroundColor: '#E8B48E' }}
              />
              <button
                className={`skin-button ${skinTone === 'medium_white_to_olive' ? 'selected' : ''}`}
                onClick={() => handleSkinToneSelect('medium_white_to_olive')}
                style={{ backgroundColor: '#D49E7B' }}
              />
              <button
                className={`skin-button ${skinTone === 'olive_tone' ? 'selected' : ''}`}
                onClick={() => handleSkinToneSelect('olive_tone')}
                style={{ backgroundColor: '#B9774B' }}
              />
              <button
                className={`skin-button ${skinTone === 'light_brown' ? 'selected' : ''}`}
                onClick={() => handleSkinToneSelect('light_brown')}
                style={{ backgroundColor: '#A65E24' }}
              />
              <button
                className={`skin-button ${skinTone === 'dark_brown' ? 'selected' : ''}`}
                onClick={() => handleSkinToneSelect('dark_brown')}
                style={{ backgroundColor: '#3E211D' }}
              />
            </div>
          </div>
        </div>
      )}

      {showThirdPanel && (
        <div className="panel" ref={thirdPanelRef}>
          <p className="panel-text">May we take a photo of you to help us find your past more easily?</p>
          <div className="buttons">
            <button
              className={`option-button ${useSelfie === true ? 'selected' : ''}`}
              onClick={() => setUseSelfie(true)}
            >
              Yes, take my photo
            </button>
            <button
              className={`option-button ${useSelfie === false ? 'selected' : ''}`}
              onClick={() => setUseSelfie(false)}
            >
              No, let GenAI find it
            </button>
          </div>
        </div>
      )}

      {useSelfie !== null && (
        <button
          className="travel-button option-button"
          onClick={handleTravel}
          ref={travelButtonRef}
        >
          Click to Find
        </button>
      )}
      <br/><br/>
    </div>
    
  );
};

export default UserAsking;