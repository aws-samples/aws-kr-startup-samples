import React, { useState } from 'react';
import Modal from 'react-modal';
import { useTranslation, Trans } from 'react-i18next';
import './PrivacyModal.css';
import { Link } from 'react-router-dom';

Modal.setAppElement('#root');

const PrivacyModal = ({ isOpen, onClose, onAgree, onDisagree }) => {
  const [name, setName] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [showAlert, setShowAlert] = useState(false);
  const { t } = useTranslation();

  const handleNameChange = (e) => {
    setName(e.target.value);
  };

  const handleAgree = () => {
    if (agreed && name.trim() !== '') {
      onAgree(name);
      setShowAlert(false);
      // Modal 창만 닫기
    //   onClose();
    } else {
      setShowAlert(true);
    }
  };

  const handleDisagree = () => {
    onDisagree();
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onRequestClose={onClose}
      className="PrivacyModal"
      overlayClassName="PrivacyModal-Overlay"
    >
      <div className="PrivacyModal-Content">
        <div className="PrivacyModal-Header">
          <h2><Trans i18nKey="privacyModal.title"/></h2>
        </div>
        <div className="PrivacyModal-Body">
        <p>
            <label>
                <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                />
                <b>
                <Trans
            i18nKey="privacyModal.mandatory"
            components={[
              <a
                href={t('privacyModal.mandatoryLink')}
                target="_blank"
                rel="noopener noreferrer"
              />
            ]}
          />
                </b>
            </label>
        </p>
          <hr/>  
          <Trans
            i18nKey="privacyModal.description"
            components={[
              <a
                href={t('privacyModal.descriptionLink')}
                target="_blank"
                rel="noopener noreferrer"
              />
            ]}
          />
          <div className="PrivacyModal-Table">
            <div className="PrivacyModal-TableRow">
              <div className="PrivacyModal-TableCell"><Trans i18nKey="privacyModal.collectedItemTitle"/></div>
              <div className="PrivacyModal-TableCell"><Trans i18nKey="privacyModal.collectedItemDesc"/></div>
            </div>
            <div className="PrivacyModal-TableRow">
              <div className="PrivacyModal-TableCell"><Trans i18nKey="privacyModal.collectionUsePurposeTitle"/></div>
              <div className="PrivacyModal-TableCell">
              <Trans i18nKey="privacyModal.collectionUsePurposeDesc"/>
              </div>
            </div>
            <div className="PrivacyModal-TableRow">
              <div className="PrivacyModal-TableCell"><Trans i18nKey="privacyModal.retentionPeriodTitle"/></div>
              <div className="PrivacyModal-TableCell"><Trans i18nKey="privacyModal.retentionPeriodDesc"/></div>
            </div>
          </div>
          {/* <p>
            <Trans
            i18nKey="privacyModal.check"
            components={[
              <a
                href={t('privacyModal.checkLink')}
                target="_blank"
                rel="noopener noreferrer"
              />
            ]}
          />
            </p> */}
            <div style={{ marginTop: '10px' }}>
              <b><Trans i18nKey="privacyModal.nameInput"/></b>&nbsp;&nbsp;
              <input
                type="text"
                value={name}
                onChange={handleNameChange}
              />
            </div>
          
        </div>
        <div className="PrivacyModal-Footer">

          {showAlert && (
            <div className="PrivacyModal-Alert">
              {t('privacyModal.message')}
            </div>
          )}
          <div className="PrivacyModal-Buttons">
            <button
              className="PrivacyModal-Button PrivacyModal-Disagree"
              onClick={handleDisagree}
            >
              {t('privacyModal.buttonDisagree')}
            </button>
            <button
              className="PrivacyModal-Button PrivacyModal-Agree"
              onClick={handleAgree}
            >
              {t('privacyModal.buttonAgree')}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default PrivacyModal;