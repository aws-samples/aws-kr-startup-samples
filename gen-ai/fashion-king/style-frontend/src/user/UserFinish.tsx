import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './UserFinish.css';

const UserFinish: React.FC = () => {
  const [timer, setTimer] = useState(15);
  const navigate = useNavigate();

  useEffect(() => {
    const interval = setInterval(() => {
      setTimer((prev) => prev - 1);
    }, 1000);

    if (timer === 0) {
      clearInterval(interval);
      navigate('/user/start');
    }

    return () => clearInterval(interval);
  }, [timer, navigate]);

  const handleClick = () => {
    navigate('/user/start');
  };

  return (
    <div className="user-finish-container">
      <div className="user-finish-background"></div>
      <div className="user-finish-content">
        <h2 className="title">We are searching for your past life.<br/>Wait and see the display.</h2>
        <p className="timer">Move to the start page in <span className="timer-count">{timer}</span> seconds</p>
        <button className="go-start-button" onClick={handleClick}>
          Click To Start
        </button>
      </div>
    </div>
  );
};

export default UserFinish;