import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Button,
  Alert,
  Spinner,
  Box,
  Select,
  DatePicker,
  TimeInput,
  ColumnLayout,
  Checkbox,
} from '@cloudscape-design/components';

const API_HOST = process.env.REACT_APP_API_HOST || '';
const GENERATE_API_ENDPOINT = `${API_HOST}/apis/videos/generate`;
const SCHEDULE_API_ENDPOINT = `${API_HOST}/apis/videos/schedule`;

function GenerateVideo({ /* 기존 props */ }) {
  const [prompt, setPrompt] = useState('');
  const [numShots, setNumShots] = useState({ value: 2, label: '2 shots' });
  const [imageData, setImageData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const [enableScheduling, setEnableScheduling] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endDate, setEndDate] = useState('');
  const [endTime, setEndTime] = useState('');
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleId, setScheduleId] = useState('');
  const [scheduleErrorMessage, setScheduleErrorMessage] = useState('');
  const [scheduleSuccessMessage, setScheduleSuccessMessage] = useState('');

  const combineAndConvertToUTC = useCallback((dateStr, timeStr) => {
    if (!dateStr || !timeStr || !/^\d{4}\/\d{2}\/\d{2}$/.test(dateStr) || !/^\d{2}:\d{2}:\d{2}$/.test(timeStr)) {
      console.error("Invalid date or time format for conversion:", dateStr, timeStr);
      return null;
    }
    try {
      const localDate = new Date(`${dateStr.replace(/\//g, '-')}T${timeStr}`);
      if (isNaN(localDate.getTime())) {
        throw new Error("Invalid date/time combination");
      }
      return localDate.toISOString().split('.')[0] + 'Z';
    } catch (e) {
      console.error("Error converting date/time to UTC:", e);
      return null;
    }
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!prompt) {
      setErrorMessage('Please enter a prompt.');
      return;
    }
    setIsLoading(true);
    setErrorMessage('');
    setSuccessMessage('');
    setScheduleErrorMessage('');
    setScheduleSuccessMessage('');

    const payload = {
      prompt,
      num_shots: numShots?.value || 2,
    };

    try {
      const response = await fetch(GENERATE_API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setSuccessMessage(`Video generation started (ID: ${data.invocationId}). Check status below.`);
    } catch (error) {
      console.error("Error generating video:", error);
      setErrorMessage('Error starting video generation: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  }, [prompt, numShots]);

  const handleSchedule = useCallback(async () => {
    const utcStartTime = combineAndConvertToUTC(startDate, startTime);
    const utcEndTime = combineAndConvertToUTC(endDate, endTime);

    if (!prompt || !utcStartTime || !utcEndTime) {
      setScheduleErrorMessage('Please enter prompt, valid start date/time, and end date/time (UTC will be calculated).');
      return;
    }
    if (new Date(utcStartTime) >= new Date(utcEndTime)) {
      setScheduleErrorMessage('End time must be after start time.');
      return;
    }

    setIsScheduling(true);
    setErrorMessage('');
    setSuccessMessage('');
    setScheduleErrorMessage('');
    setScheduleSuccessMessage('');
    setScheduleId('');

    try {
      const response = await fetch(SCHEDULE_API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          startTime: utcStartTime,
          endTime: utcEndTime,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setScheduleSuccessMessage(`Video generation scheduled successfully (ID: ${data.scheduleId}).`);
      setScheduleId(data.scheduleId);
    } catch (error) {
      console.error("Error scheduling video generation:", error);
      setScheduleErrorMessage('Error creating schedule: ' + error.message);
    } finally {
      setIsScheduling(false);
    }
  }, [prompt, startDate, startTime, endDate, endTime, combineAndConvertToUTC]);

  const handleDeleteSchedule = useCallback(async () => {
    if (!scheduleId) return;

    const confirmDelete = window.confirm(`Are you sure you want to delete schedule ${scheduleId}?`);
    if (!confirmDelete) return;

    setIsLoading(true);
    setErrorMessage('');
    setSuccessMessage('');
    setScheduleErrorMessage('');
    setScheduleSuccessMessage('');

    try {
      const deleteUrl = `${SCHEDULE_API_ENDPOINT}/${scheduleId}`;
      const response = await fetch(deleteUrl, { method: 'DELETE' });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 404) {
            setScheduleSuccessMessage(`Schedule ${scheduleId} was already deleted or not found.`);
        } else {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
      } else {
          setScheduleSuccessMessage(`Schedule ${scheduleId} deleted successfully.`);
      }
      setScheduleId('');
    } catch (error) {
      console.error("Error deleting schedule:", error);
      setScheduleErrorMessage('Error deleting schedule: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  }, [scheduleId]);

  const getTodayDateString = () => {
      const today = new Date();
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const day = String(today.getDate()).padStart(2, '0');
      return `${year}/${month}/${day}`;
  };

  return (
    <Container header={<Header variant="h2">Generate Video</Header>}>
      <SpaceBetween direction="vertical" size="l">
        {errorMessage && <Alert type="error" dismissible onDismiss={() => setErrorMessage('')}>{errorMessage}</Alert>}
        {successMessage && <Alert type="success" dismissible onDismiss={() => setSuccessMessage('')}>{successMessage}</Alert>}
        {scheduleErrorMessage && <Alert type="error" dismissible onDismiss={() => setScheduleErrorMessage('')}>{scheduleErrorMessage}</Alert>}
        {scheduleSuccessMessage && <Alert type="success" dismissible onDismiss={() => setScheduleSuccessMessage('')}>{scheduleSuccessMessage}</Alert>}

        <FormField label="Prompt" description="Enter the prompt for video generation." stretch={true}>
          <Input
            value={prompt}
            onChange={event => setPrompt(event.detail.value)}
            placeholder="e.g., a cat riding a skateboard in space"
            disabled={isLoading || isScheduling}
          />
        </FormField>
        {/* <FormField label="Number of Shots">
          <Select
            selectedOption={numShots}
            onChange={({ detail }) => setNumShots(detail.selectedOption)}
            options={[ { value: 1, label: '1 shot' }, { value: 2, label: '2 shots' }, ... ]}
            disabled={isLoading || isScheduling}
          />
        </FormField> */}
        {/* TODO: 이미지 업로드 등 기존 UI 요소들 */}

        <FormField>
          <Checkbox
            checked={enableScheduling}
            onChange={({ detail }) => {
              setEnableScheduling(detail.checked);
              if (!detail.checked) {
                setStartDate(''); setStartTime(''); setEndDate(''); setEndTime('');
                setScheduleErrorMessage(''); setScheduleSuccessMessage(''); setScheduleId('');
              }
            }}
            disabled={isLoading || isScheduling}
          >
            Schedule this video generation (runs every 5 minutes between start/end times)
          </Checkbox>
        </FormField>

        {enableScheduling && (
          <Box margin={{ top: 'm' }} padding="m" variant="div" >
            <Header variant="h3">Schedule Details</Header>
            <SpaceBetween direction="vertical" size="m">
              <FormField
                label="Start Date and Time (Local)"
                description="Select the date and time when scheduled generation should begin."
                errorText={!startDate || !startTime ? "Start date and time are required." : ""}
              >
                <ColumnLayout columns={2}>
                  <DatePicker
                    onChange={({ detail }) => setStartDate(detail.value)}
                    value={startDate}
                    placeholder="YYYY/MM/DD"
                    isDateEnabled={date => {
                        const today = new Date(getTodayDateString());
                        return date >= today;
                    }}
                    disabled={isScheduling}
                  />
                  <TimeInput
                    onChange={({ detail }) => setStartTime(detail.value)}
                    value={startTime}
                    format="hh:mm:ss"
                    placeholder="HH:MM:SS"
                    disabled={isScheduling}
                  />
                </ColumnLayout>
              </FormField>
              <FormField
                label="End Date and Time (Local)"
                description="Select the date and time when scheduled generation should stop."
                 errorText={!endDate || !endTime ? "End date and time are required." : ""}
             >
                <ColumnLayout columns={2}>
                  <DatePicker
                    onChange={({ detail }) => setEndDate(detail.value)}
                    value={endDate}
                    placeholder="YYYY/MM/DD"
                    isDateEnabled={date => {
                        if (!startDate) return true;
                        const startDt = new Date(startDate.replace(/\//g, '-'));
                        return date >= startDt;
                    }}
                    disabled={isScheduling || !startDate}
                  />
                  <TimeInput
                    onChange={({ detail }) => setEndTime(detail.value)}
                    value={endTime}
                    format="hh:mm:ss"
                    placeholder="HH:MM:SS"
                    disabled={isScheduling || !startDate || !startTime}
                  />
                </ColumnLayout>
              </FormField>
            </SpaceBetween>
          </Box>
        )}

        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              variant="primary"
              onClick={handleGenerate}
              loading={isLoading}
              disabled={enableScheduling || isScheduling || isLoading}
            >
              Generate Now
            </Button>

            <Button
              variant={enableScheduling ? "primary" : "normal"}
              onClick={handleSchedule}
              loading={isScheduling}
              disabled={!enableScheduling || isLoading || isScheduling}
            >
              Schedule Generation
            </Button>

            {scheduleId && (
              <Button
                variant="warning"
                iconName="delete"
                onClick={handleDeleteSchedule}
                loading={isLoading}
                disabled={isLoading || isScheduling}
                ariaLabel={`Delete schedule ${scheduleId}`}
              >
                Delete Schedule
              </Button>
            )}
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    </Container>
  );
}

export default GenerateVideo; 