import * as React from "react";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import FormField from "@cloudscape-design/components/form-field";
import Textarea from "@cloudscape-design/components/textarea";
import Alert from "@cloudscape-design/components/alert";
import HelpPanel from "@cloudscape-design/components/help-panel";
import Icon from "@cloudscape-design/components/icon";
import AppLayout from "@cloudscape-design/components/app-layout";
import PromptInput from "@cloudscape-design/components/prompt-input";
import FileUpload from "@cloudscape-design/components/file-upload";
import ChatBubble from "@cloudscape-design/chat-components/chat-bubble";
import Avatar from "@cloudscape-design/chat-components/avatar";
import ReactMarkdown from 'react-markdown';
import { generateVideo, chatNova } from "../../utils/api";
import DatePicker from "@cloudscape-design/components/date-picker";
import TimeInput from "@cloudscape-design/components/time-input";
import Checkbox from "@cloudscape-design/components/checkbox";
import ColumnLayout from "@cloudscape-design/components/column-layout";

const API_HOST = process.env.REACT_APP_API_HOST || '';
const SCHEDULE_API_ENDPOINT = `${API_HOST}/apis/videos/schedule`;

export default function GenerateForm() {
  const [prompt, setPrompt] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [showSuccess, setShowSuccess] = React.useState(false);
  const [toolsOpen, setToolsOpen] = React.useState(false);
  const [chatValue, setChatValue] = React.useState("");
  const [chatMessages, setChatMessages] = React.useState([]);
  const [imageData, setImageData] = React.useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = React.useState(null);
  const [selectedFiles, setSelectedFiles] = React.useState([]);
  const [imageError, setImageError] = React.useState(null);
  
  const [enableScheduling, setEnableScheduling] = React.useState(false);
  const [startDate, setStartDate] = React.useState('');
  const [startTime, setStartTime] = React.useState('');
  const [endDate, setEndDate] = React.useState('');
  const [endTime, setEndTime] = React.useState('');
  const [isScheduling, setIsScheduling] = React.useState(false);
  const [scheduleId, setScheduleId] = React.useState('');
  const [scheduleErrorMessage, setScheduleErrorMessage] = React.useState('');
  const [scheduleSuccessMessage, setScheduleSuccessMessage] = React.useState('');

  const combineAndConvertToUTC = (dateStr, timeStr) => {
    // Check if dateStr is in 2025-04-19 format or 2025/04/19 format
    if (!dateStr || !timeStr) {
      console.error("Date or time is empty:", dateStr, timeStr);
      return null;
    }
    
    // Check if date format is YYYY-MM-DD or YYYY/MM/DD
    const dateRegex = /^\d{4}[-\/]\d{2}[-\/]\d{2}$/;
    // Check if time format is HH:MM:SS or HH:MM
    const timeRegex = /^\d{2}:\d{2}(:\d{2})?$/;
    
    if (!dateRegex.test(dateStr) || !timeRegex.test(timeStr)) {
      console.error("Invalid date or time format:", dateStr, timeStr);
      return null;
    }
    
    try {
      // Convert input date string to unified format (remove / or -)
      const dateParts = dateStr.split(/[-\/]/).map(Number); // Split by slash or dash
      const [year, month, day] = dateParts;
      
      // Parse time string (set seconds to 00 if not provided)
      let [hours, minutes, seconds] = timeStr.split(':').map(Number);
      if (seconds === undefined) seconds = 0;
      
      console.log(`Date/time to convert: ${year}-${month}-${day} ${hours}:${minutes}:${seconds} (KST)`);
      
      // Create Date object in Korean time (KST) and convert to UTC
      const koreaDate = new Date(Date.UTC(year, month - 1, day, hours - 9, minutes, seconds));
      
      // Verify valid date
      if (isNaN(koreaDate.getTime())) {
        throw new Error(`Invalid date/time: ${dateStr} ${timeStr}`);
      }
      
      console.log(`Converted UTC time:`, koreaDate.toISOString());
      
      // Convert to ISO format (UTC based)
      return koreaDate.toISOString().split('.')[0] + 'Z';
    } catch (e) {
      console.error("Date/time UTC conversion error:", e);
      return null;
    }
  };

  const getTodayDateString = () => {
    // Calculate today's date in Korean time (UTC+9)
    const now = new Date();
    
    // Current system's local timezone offset (minutes)
    const localOffset = now.getTimezoneOffset();
    
    // Korean timezone (KST) is UTC+9, so offset is -540 minutes (9 hours * 60 minutes)
    const kstOffset = -540;
    
    // Difference between local timezone and KST (minutes)
    const offsetDiff = localOffset + kstOffset;
    
    // Apply offset difference to current time to calculate KST time
    const koreaTime = new Date(now.getTime() + offsetDiff * 60 * 1000);
    
    const year = koreaTime.getFullYear();
    const month = String(koreaTime.getMonth() + 1).padStart(2, '0');
    const day = String(koreaTime.getDate()).padStart(2, '0');
    
    console.log(`Current Korean time: ${koreaTime.toISOString()} (${year}/${month}/${day})`);
    
    return `${year}/${month}/${day}`;
  };

  const validateImageDimensions = (dataUrl) => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        if (img.width === 1280 && img.height === 720) {
          setImageError(null);
          resolve(true);
        } else {
          const errorMsg = `Image resolution is not 1280x720 pixels. Current resolution: ${img.width}x${img.height}`;
          setImageError(errorMsg);
          reject(new Error(errorMsg));
        }
      };
      img.onerror = () => {
        setImageError("Error occurred while loading image.");
        reject(new Error("Image load error"));
      };
      img.src = dataUrl;
    });
  };

  const handleFileChange = (event) => {
    const files = event.detail.value;
    setSelectedFiles(files);
    setImageError(null);
    
    if (files && files.length > 0) {
      const file = files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target.result;
        setImagePreviewUrl(dataUrl);
        
        validateImageDimensions(dataUrl)
          .then(() => {
            const base64Image = dataUrl.split(',')[1];
            setImageData(base64Image);
          })
          .catch((error) => {
            console.error("Image validation error:", error.message);
            setImageData(null);
          });
      };
      reader.readAsDataURL(file);
    } else {
      setImageData(null);
      setImagePreviewUrl(null);
      setImageError(null);
    }
  };

  const handleFileRemove = (event) => {
    setSelectedFiles([]);
    setImageData(null);
    setImagePreviewUrl(null);
    setImageError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (imagePreviewUrl && !imageData) {
      return;
    }
    
    setLoading(true);
    
    try {
      await generateVideo(prompt, imageData);
      setShowSuccess(true);
      setTimeout(() => {
        window.location.hash = "#/outputs";
      }, 3000);
    } catch (error) {
      console.error("Failed to generate video:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();

    if (chatValue.trim()) {
      const newMsgs = [...chatMessages];
      newMsgs.push({
        role: 'user',
        content: chatValue,
        loading: false
      });
      newMsgs.push({
        role: 'assistant',
        content: "Generating response",
        loading: true
      });

      setChatMessages(newMsgs)

      const res = await chatNova(newMsgs);
      newMsgs[newMsgs.length-1].content = res.message
      newMsgs[newMsgs.length-1].loading = false

      setChatMessages(newMsgs)

      setChatValue("");
    }
  };

  const handleSchedule = async (e) => {
    e.preventDefault();
    
    // 입력값 검증
    if (!prompt.trim()) {
      setScheduleErrorMessage('Enter a description of the video you want to generate.');
      return;
    }
    
    if (!startDate || !startTime) {
      setScheduleErrorMessage('Start date and time are required.');
      return;
    }
    
    if (!endDate || !endTime) {
      setScheduleErrorMessage('End date and time are required.');
      return;
    }
    
    // 날짜 변환
    const utcStartTime = combineAndConvertToUTC(startDate, startTime);
    const utcEndTime = combineAndConvertToUTC(endDate, endTime);
    
    if (!utcStartTime || !utcEndTime) {
      setScheduleErrorMessage('Invalid date/time format. Please enter again.');
      return;
    }
    
    // 시간 비교 (UTC 기준)
    const startDateTime = new Date(utcStartTime);
    const endDateTime = new Date(utcEndTime);
    
    // 시작 시간과 종료 시간에 밀리초 단위 무시를 위해 설정
    startDateTime.setMilliseconds(0);
    endDateTime.setMilliseconds(0);
    
    console.log('Start time (UTC):', startDateTime.toISOString());
    console.log('End time (UTC):', endDateTime.toISOString());
    
    // 종료 시간이 시작 시간보다 나중인지 확인 (밀리초 무시하고 정확히 비교)
    if (startDateTime.getTime() >= endDateTime.getTime()) {
      setScheduleErrorMessage('End time must be after start time.');
      return;
    }

    // 상태 초기화 및 로딩 상태 설정
    setIsScheduling(true);
    setScheduleErrorMessage('');
    setScheduleSuccessMessage('');
    setScheduleId('');

    try {
      console.log('Schedule request data:', {
        prompt,
        startTime: utcStartTime,
        endTime: utcEndTime
      });
      
      const response = await fetch(SCHEDULE_API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          startTime: utcStartTime,
          endTime: utcEndTime,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error (status code: ${response.status})`);
      }
      
      const data = await response.json();
      console.log('Schedule response data:', data);
      
      setScheduleSuccessMessage(`Video generation schedule set successfully. (ID: ${data.scheduleId || data.scheduleName || 'Created'})`);
      setScheduleId(data.scheduleId || data.scheduleName || 'schedule-created');
    } catch (error) {
      console.error("Schedule error:", error);
      setScheduleErrorMessage('Schedule creation error: ' + (error.message || 'Server communication error occurred.'));
    } finally {
      setIsScheduling(false);
    }
  };

  const handleDeleteSchedule = async (e) => {
    e.preventDefault();
    
    if (!scheduleId) {
      setScheduleErrorMessage('No schedule to delete.');
      return;
    }
    
    const confirmDelete = window.confirm(`Are you sure you want to delete this schedule?`);
    if (!confirmDelete) return;

    setIsScheduling(true);
    setScheduleErrorMessage('');
    setScheduleSuccessMessage('');

    try {
      console.log('Schedule delete request:', scheduleId);
      
      const response = await fetch(SCHEDULE_API_ENDPOINT, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error (status code: ${response.status})`);
      }
      
      const data = await response.json();
      console.log('Schedule delete response:', data);
      
      setScheduleSuccessMessage(`Schedule deleted successfully.`);
      
      // 상태 초기화
      setScheduleId('');
      setEnableScheduling(false);
      setStartDate('');
      setStartTime('');
      setEndDate('');
      setEndTime('');
    } catch (error) {
      console.error("Schedule delete error:", error);
      setScheduleErrorMessage('Schedule delete error: ' + (error.message || 'Server communication error occurred.'));
    } finally {
      setIsScheduling(false);
    }
  };

  return (
    <>
      <AppLayout
        content={
          <Box margin={{ bottom: "l" }}>
            <SpaceBetween size="l">
              <Header variant="h1">Video Generation</Header>
              
              {showSuccess && (
                <Alert
                  dismissible
                  onDismiss={() => setShowSuccess(false)}
                  statusIconAriaLabel="Success"
                  type="success"
                >
                  Video generation request submitted successfully.
                  Redirecting to output page...
                </Alert>
              )}
              
              {scheduleErrorMessage && (
                <Alert
                  dismissible
                  onDismiss={() => setScheduleErrorMessage('')}
                  statusIconAriaLabel="Error"
                  type="error"
                >
                  {scheduleErrorMessage}
                </Alert>
              )}
              
              {scheduleSuccessMessage && (
                <Alert
                  dismissible
                  onDismiss={() => setScheduleSuccessMessage('')}
                  statusIconAriaLabel="Success"
                  type="success"
                >
                  {scheduleSuccessMessage}
                </Alert>
              )}

              <form style={{ width: '100%' }}>
                <SpaceBetween size="l">
                  <FormField
                    label="Prompt"
                    description="Enter a description of the video you want to generate"
                    stretch
                  >
                    <Textarea
                      value={prompt}
                      onChange={({ detail }) => setPrompt(detail.value)}
                      placeholder="Ex) Slow cam of a man middle age; 4k; Cinematic; in a sunny day; peaceful; highest quality; dolly in;"
                      rows={3}
                      stretch
                    />
                  </FormField>

                  <FormField
                    label="Reference Image (Optional)"
                    description="Upload a reference image for video generation"
                    stretch
                  >
                    <SpaceBetween size="m">
                      <FileUpload
                        onChange={handleFileChange}
                        onFileRemove={handleFileRemove}
                        value={selectedFiles}
                        i18nStrings={{
                          uploadButtonText: e =>
                            e ? "Choose another file" : "Choose file",
                          dropzoneText: e =>
                            e
                              ? "Drop file to replace"
                              : "Drop file here or choose a file",
                          removeFileAriaLabel: e => `Remove file ${e}`,
                          limitShowFewer: "Show fewer",
                          limitShowMore: "Show more",
                          errorIconAriaLabel: "Error",
                          readButtonText: "View filename",
                          selectedFileLabel: (e, n) => `Selected file: ${e}`,
                          selectedFilesLabel: (e, n) => `Selected files: ${e}`,
                          previewLabel: "Image preview"
                        }}
                        accept="image/*"
                        multiple={false}
                        constraintText="Only image files are supported."
                      />
                      
                      {imagePreviewUrl && (
                        <div style={{ marginTop: '10px' }}>
                          <p>Preview:</p>
                          <img 
                            src={imagePreviewUrl} 
                            alt="Upload preview" 
                            style={{ maxWidth: '100%', maxHeight: '200px', marginTop: '5px' }} 
                          />
                          {imageError && (
                            <Alert
                              type="error"
                              statusIconAriaLabel="Error"
                              header="Image Resolution Error"
                              dismissible={false}
                            >
                              {imageError}
                              <div style={{ marginTop: '5px' }}>
                                Image resolution must be exactly 1280x720 pixels.
                              </div>
                            </Alert>
                          )}
                        </div>
                      )}
                    </SpaceBetween>
                  </FormField>
                  
                  <FormField>
                    <Checkbox
                      checked={enableScheduling}
                      onChange={({ detail }) => {
                        setEnableScheduling(detail.checked);
                        if (!detail.checked) {
                          setStartDate(''); 
                          setStartTime(''); 
                          setEndDate(''); 
                          setEndTime('');
                          setScheduleErrorMessage(''); 
                          setScheduleSuccessMessage(''); 
                          setScheduleId('');
                        }
                      }}
                      disabled={loading || isScheduling}
                    >
                      Schedule this video generation (runs every 5 minutes between start/end times)
                    </Checkbox>
                  </FormField>
                  
                  {enableScheduling && (
                    <Box margin={{ top: 'm' }} padding="m" variant="div" >
                      <Header variant="h3">Schedule Details</Header>
                      <SpaceBetween direction="vertical" size="m">
                        <FormField
                          label="Start Date and Time (Korean Time - KST)"
                          description="Select the date and time when the scheduled video generation should start."
                          errorText={!startDate || !startTime ? "Start date and time are required." : ""}
                        >
                          <ColumnLayout columns={2}>
                            <DatePicker
                              key="start-date-picker"
                              onChange={({ detail }) => setStartDate(detail.value)}
                              value={startDate}
                              placeholder="YYYY/MM/DD"
                              isDateEnabled={date => {
                                  // Calculate today's date in Korean time
                                  const todayString = getTodayDateString();
                                  const today = new Date(todayString.replace(/\//g, '-'));
                                  today.setHours(0, 0, 0, 0); // Set time to 00:00:00
                                  
                                  // Copy date object for comparison
                                  const checkDate = new Date(date.getTime());
                                  checkDate.setHours(0, 0, 0, 0);
                                  
                                  // Output debug information
                                  console.log(`Date comparison: checkDate=${checkDate.toISOString()}, today=${today.toISOString()}, result=${checkDate >= today}`);
                                  
                                  // Enable dates from today onwards
                                  return checkDate >= today;
                              }}
                              disabled={isScheduling}
                              id="start-date-picker"
                            />
                            
                            <TimeInput
                              key="start-time-input"
                              onChange={({ detail }) => setStartTime(detail.value)}
                              value={startTime}
                              format="hh:mm:ss"
                              placeholder="HH:MM:SS"
                              disabled={isScheduling}
                              id="start-time-input"
                            />
                          </ColumnLayout>
                        </FormField>
                        <FormField
                          label="End Date and Time (Korean Time - KST)"
                          description="Select the date and time when the scheduled video generation should stop."
                          errorText={!endDate || !endTime ? "End date and time are required." : ""}
                        >
                          <ColumnLayout columns={2}>
                            <DatePicker
                              key="end-date-picker"
                              onChange={({ detail }) => setEndDate(detail.value)}
                              value={endDate}
                              placeholder="YYYY/MM/DD"
                              isDateEnabled={date => {
                                  // Calculate today's date in Korean time
                                  const todayString = getTodayDateString();
                                  const today = new Date(todayString.replace(/\//g, '-'));
                                  today.setHours(0, 0, 0, 0); // Set time to 00:00:00
                                  
                                  // Copy date object for comparison
                                  const checkDate = new Date(date.getTime());
                                  checkDate.setHours(0, 0, 0, 0);
                                  
                                  // If start date is set
                                  if (startDate) {
                                      const startDt = new Date(startDate.replace(/\//g, '-'));
                                      startDt.setHours(0, 0, 0, 0);
                                      
                                      // If start date is in the future, only allow dates after start date
                                      if (startDt > today) {
                                          return checkDate >= startDt;
                                      }
                                  }
                                  
                                  // Enable dates from today onwards
                                  return checkDate >= today;
                              }}
                              disabled={isScheduling}
                              id="end-date-picker"
                            />
                            <TimeInput
                              key="end-time-input"
                              onChange={({ detail }) => setEndTime(detail.value)}
                              value={endTime}
                              format="hh:mm:ss"
                              placeholder="HH:MM:SS"
                              disabled={isScheduling || !startDate || !startTime}
                              id="end-time-input"
                            />
                          </ColumnLayout>
                        </FormField>
                      </SpaceBetween>
                    </Box>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <SpaceBetween direction="horizontal" size="xs">
                      <Button 
                        key="ai-assist-button"
                        variant="normal"
                        onClick={(e) => {
                          e.preventDefault();
                          setToolsOpen(!toolsOpen);
                        }}
                      >
                        AI Assistant
                      </Button>
                      
                      {enableScheduling ? (
                        <Button
                          key="schedule-button"
                          variant="primary"
                          onClick={handleSchedule}
                          loading={isScheduling}
                          disabled={!enableScheduling || loading || isScheduling}
                        >
                          Schedule
                        </Button>
                      ) : (
                        <Button 
                          key="generate-button"
                          variant="primary" 
                          onClick={handleSubmit}
                          loading={loading}
                          disabled={(!prompt.trim() && !imageData) || loading || (imagePreviewUrl && !imageData)}
                        >
                          Generate
                        </Button>
                      )}
                      
                      {scheduleId && (
                        <Button
                          key="delete-schedule-button"
                          variant="warning"
                          iconName="delete"
                          onClick={handleDeleteSchedule}
                          loading={isScheduling}
                          disabled={loading || isScheduling}
                        >
                          Delete Schedule
                        </Button>
                      )}
                    </SpaceBetween>
                  </div>

                  <div>
                      <div>
                      <h2>Tips for Effective Prompting:</h2>
                      </div>
                      
                      <h3>Prompt Structure</h3>
                      <ul>
                        {[
                          "Describe the scene as a caption rather than a command",
                          "Separate details with semicolons (;)",
                          "Add camera movements at the beginning or end of your prompt",
                          "Keep prompts under 512 characters",
                          "Avoid negation words like \"no\", \"not\", \"without\""
                        ].map((item, index) => (
                          <li key={`prompt-structure-${index}`}>{item}</li>
                        ))}
                      </ul>

                      <h3>Image-to-Video Generation</h3>
                      <ul>
                        {[
                          "Upload a reference image to create videos with similar visual style",
                          "Use clear, high-quality images for better results",
                          "Combine with descriptive prompts to guide the video direction",
                          "The image influences visual style, while the prompt controls content and movement"
                        ].map((item, index) => (
                          <li key={`image-to-video-${index}`}>{item}</li>
                        ))}
                      </ul>

                      <h3>Recommended Keywords</h3>
                      <p>
                        {['4k', 'cinematic', 'high quality', 'detailed', 'realistic', 'slow motion', 'dolly zoom'].map((keyword, index) => (
                          <code key={`keyword-${index}`} style={{marginRight: '8px'}}>{keyword}</code>
                        ))}
                      </p>

                      <h3>Refinement Techniques</h3>
                      <ul>
                        {[
                          "Use consistent seed values when making small prompt changes",
                          "Generate multiple variations with different seeds once you're satisfied"
                        ].map((item, index) => (
                          <li key={`refinement-${index}`}>{item}</li>
                        ))}
                      </ul>

                      <h3>Example Prompts</h3>
                      <pre>
        Slow cam of a man middle age; 4k; Cinematic; in a sunny day; peaceful; highest quality; dolly in;
                      </pre>
                      <pre>
        Closeup of a large seashell in the sand. Gentle waves flow around the shell. Camera zoom in.
                      </pre>
                  </div>

                  <div>
                      <h3>
                          Learn More{" "}
                          <Icon name="external" size="inherit" />
                      </h3>
                      <ul>
                          {[
                            {
                              href: "https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-generation.html",
                              text: "Amazon Nova Reel prompting best practices"
                            },
                            {
                              href: "https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-image-prompts.html",
                              text: "Image-based video generation prompts"
                            },
                            {
                              href: "https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-camera-control.html",
                              text: "Camera controls"
                            }
                          ].map((link, index) => (
                            <li key={`learn-more-${index}`}>
                              <a href={link.href} target="_blank" rel="noopener noreferrer">
                                {link.text}
                              </a>
                            </li>
                          ))}
                      </ul>
                  </div>
                </SpaceBetween>
              </form>
            </SpaceBetween>
          </Box>
        }
        tools={
          <HelpPanel
            header={<h2>Amazon Nova Chat</h2>}
            iconName="gen-ai"
          >
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              height: 'calc(100vh - 120px)', 
              justifyContent: 'space-between' 
            }}>
              <div style={{ overflowY: 'auto' }}>
                {chatMessages.map((message, index) => (
                  <span key={`message-${index}`}>
                    <ChatBubble
                      avatar={message.role === 'user' ? <Avatar /> : <Avatar color="gen-ai" initials="AI" loading={message.loading}/>}
                      type='incoming'
                    >
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </ChatBubble>
                    <br />
                  </span>
                ))}
              </div>
              <div style={{ position: 'sticky', bottom: 0, backgroundColor: 'white', paddingTop: '16px' }}>
                <PromptInput
                  onChange={({ detail }) => setChatValue(detail.value)}
                  value={chatValue}
                  onAction={handleChatSubmit}
                  actionButtonAriaLabel="Send message"
                  actionButtonIconName="send"
                  ariaLabel="Prompt input with min and max rows"
                  maxRows={8}
                  minRows={3}
                  placeholder="Ask a question"
                />
              </div>
            </div>
          </HelpPanel>
        }
        toolsOpen={toolsOpen}
        onToolsChange={({ detail }) => setToolsOpen(detail.open)}
        navigationHide={true}
        toolsWidth="400"
      />
    </>
  );
} 