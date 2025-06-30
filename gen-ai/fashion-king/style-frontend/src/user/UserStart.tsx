import React from 'react';
import './UserStart.css'
import { useNavigate } from 'react-router-dom';
import backgroundImage from '../assets/bg-1.png';
import { useTranslation } from 'react-i18next';

const UserStart = ({ signOut, user }) => {
    const navigate = useNavigate();
    const { t } = useTranslation();

    const handleButtonClick = () => {
        navigate('/user/ask');
    };

    return (
      <div className="user-start" style={{ backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url(${backgroundImage})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
        <div className="gallery-title">
            <br/>{t('welcome')}<br/><br/>
            <div style={{ fontSize: 33, fontFamily: 'Geogia'}}>
            {t('welcomeDesc')}
            </div>
        </div>
        
        <div className="content-container">
          <div className="start-button">
            <button onClick={handleButtonClick} className="user-start-button">
              {t('startButton')}
            </button>
          </div>        
        </div>

        <div className="copyright">
            <div>
            <button 
                onClick={signOut}
                style={{
                    background: 'transparent',
                    color: 'white',
                    padding: '8px 20px',
                    cursor: 'pointer',
                    fontSize: '0.2rem',
                }}
            >{user.username}</button>
            </div>
          &copy; {new Date().getFullYear()} Amazon Web Services, Inc. All rights reserved.
        </div>
      </div>  
    );
}

export default UserStart;