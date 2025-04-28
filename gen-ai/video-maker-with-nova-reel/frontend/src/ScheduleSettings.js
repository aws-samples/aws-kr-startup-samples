import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Toggle,
  Button,
  Alert,
  Spinner,
  Box,
  Select
} from '@cloudscape-design/components';

// API Gateway 엔드포인트 URL (환경 변수에서 가져오는 것이 가장 좋습니다)
const API_HOST = process.env.REACT_APP_API_HOST || ''; // .env 파일에서 설정 필요
const SCHEDULE_API_ENDPOINT = `${API_HOST}/apis/schedule`;

// 시간대 옵션 (IANA 형식)
const timezoneOptions = [
  { label: "UTC", value: "UTC" },
  { label: "서울 (Asia/Seoul)", value: "Asia/Seoul" },
  { label: "뉴욕 (America/New_York)", value: "America/New_York" },
  { label: "런던 (Europe/London)", value: "Europe/London" },
  { label: "도쿄 (Asia/Tokyo)", value: "Asia/Tokyo" },
  { label: "시드니 (Australia/Sydney)", value: "Australia/Sydney" },
  // 필요한 만큼 더 추가
];

function ScheduleSettings() {
  const [prompt, setPrompt] = useState('');
  const [isEnabled, setIsEnabled] = useState(false);
  const [selectedTimezone, setSelectedTimezone] = useState(null); // 시간대 상태 추가 (Select 컴포넌트용)
  const [isLoading, setIsLoading] = useState(true); // 초기 로딩 상태
  const [isSaving, setIsSaving] = useState(false); // 저장 중 상태
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // 컴포넌트 마운트 시 현재 설정 불러오기
  useEffect(() => {
    const fetchSettings = async () => {
      setIsLoading(true);
      setErrorMessage('');
      try {
        const response = await fetch(SCHEDULE_API_ENDPOINT, { method: 'GET' });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setPrompt(data.prompt || ''); // 기본값 처리
        setIsEnabled(data.isEnabled || false); // 기본값 처리
        // 불러온 시간대 값으로 Select 상태 설정
        const timezoneValue = data.timezone || 'UTC'; // 기본값 UTC
        const foundOption = timezoneOptions.find(opt => opt.value === timezoneValue);
        setSelectedTimezone(foundOption || timezoneOptions[0]); // 찾거나 기본 UTC 옵션 사용
        console.log("Fetched settings:", data);
      } catch (error) {
        console.error("Error fetching schedule settings:", error);
        setErrorMessage('스케줄 설정을 불러오는 중 오류가 발생했습니다: ' + error.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSettings();
  }, []); // 빈 배열은 마운트 시 한 번만 실행되도록 함

  // 설정 저장 핸들러
  const handleSave = async () => {
    if (!selectedTimezone) {
        setErrorMessage('시간대를 선택해주세요.');
        return;
    }
    setIsSaving(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const response = await fetch(SCHEDULE_API_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          prompt, 
          isEnabled, 
          timezone: selectedTimezone.value // Select 상태의 value 사용
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setSuccessMessage(data.message || '스케줄 설정이 성공적으로 업데이트되었습니다.');
      console.log("Saved settings response:", data);

    } catch (error) {
      console.error("Error saving schedule settings:", error);
      setErrorMessage('스케줄 설정을 저장하는 중 오류가 발생했습니다: ' + error.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Container
      header={
        <Header variant="h2">
          자동 비디오 생성 스케줄 설정
        </Header>
      }
    >
      {isLoading ? (
        <Box textAlign="center"><Spinner /> 로딩 중...</Box>
      ) : (
        <SpaceBetween direction="vertical" size="l">
          {errorMessage && <Alert type="error">{errorMessage}</Alert>}
          {successMessage && <Alert type="success">{successMessage}</Alert>}

          <FormField
            label="반복 생성 프롬프트"
            description="5분마다 이 프롬프트를 사용하여 비디오가 자동으로 생성됩니다."
            stretch={true}
          >
            <Input
              value={prompt}
              onChange={event => setPrompt(event.detail.value)}
              placeholder="예: a beautiful sunset over the ocean"
              disabled={isSaving}
            />
          </FormField>

          <FormField
            label="시간대"
            description="스케줄 컨텍스트에 사용될 시간대입니다. (현재 rate(5 min) 표현식에는 직접 영향 없음)"
          >
            <Select
              selectedOption={selectedTimezone}
              onChange={({ detail }) => setSelectedTimezone(detail.selectedOption)}
              options={timezoneOptions}
              loadingText="시간대 로딩 중..."
              placeholder="시간대 선택"
              disabled={isSaving}
            />
          </FormField>

          <FormField
            label="자동 생성 활성화"
            description="활성화하면 5분마다 위 프롬프트를 사용하여 비디오 생성을 시도합니다."
          >
            <Toggle
              checked={isEnabled}
              onChange={({ detail }) => setIsEnabled(detail.checked)}
              disabled={isSaving}
            >
              {isEnabled ? '활성화됨' : '비활성화됨'}
            </Toggle>
          </FormField>

          <Box float="right">
            <Button
              variant="primary"
              onClick={handleSave}
              loading={isSaving}
              disabled={isLoading || !selectedTimezone} // 로딩 중이거나 시간대가 선택되지 않았으면 비활성화
            >
              설정 저장
            </Button>
          </Box>
        </SpaceBetween>
      )}
    </Container>
  );
}

export default ScheduleSettings; 