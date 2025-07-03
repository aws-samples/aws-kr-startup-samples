import React, { useState } from 'react'
import './App.css'
import { SandpackProvider, SandpackLayout, SandpackPreview } from '@codesandbox/sandpack-react'
import { Grid, Box, PromptInput, Button, ExpandableSection, Spinner } from '@cloudscape-design/components'
import { CodeView } from '@cloudscape-design/code-view';
import javascriptHighlight from "@cloudscape-design/code-view/highlight/javascript";
import { ChatBubble, Avatar } from '@cloudscape-design/chat-components';
import ReactMarkdown from 'react-markdown'


interface Message {
  content: { text: string }[];
  role: 'user' | 'assistant';
}


function App() {

  const [prompt, setPrompt] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [code, setCode] = useState<string>(`const App = () => {return <></>}; export default App;`);
  const [messages, setMessages] = useState<Message[]>([]);

  const chat = async (prompt: string) => {

    const messageWithUser = [...messages, {
      content: [{"text": prompt}],
      role: "user" as const
    }];

    setMessages(messageWithUser);
        
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          prompt: prompt,
          messages: messageWithUser
        })
      });

      const messageWithAssistant = [...messageWithUser, {
        content: [{"text": ""}],
        role: "assistant" as const
      }];

      setMessages(messageWithAssistant);
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error("Failed to get response reader");

      const messageIndex = messageWithAssistant.length - 1;
    

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = new TextDecoder().decode(value);
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            content: [{"text": newMessages[messageIndex].content[0].text + chunk}]
          };
          return newMessages;
        });

      }      
    } catch (error) {
      console.error("Error in chat function:", error);
      window.alert("Error occured")
    }
  }

  return (
    <div style={{ width: "80vw", height: "90vh" }}>
      <Grid
        gridDefinition={[
          { colspan: 6 },
          { colspan: 6 }
        ]}
        disableGutters={false}
      >
        <Box
          padding="l"
          variant="h2"
        >
          <div style={{ overflowY: "auto", marginBottom: "20px", height: "80vh"}}>
              <ChatBubble
                ariaLabel='Assistant'
                type='incoming'
                avatar={
                  <Avatar
                    color="gen-ai"
                    iconName="gen-ai"
                    ariaLabel="Generative AI assistant"
                    tooltipText="Generative AI assistant"
                  />
                }
              >
                <ReactMarkdown>
                  Feel free to ask any questions you have about AWS.
                </ReactMarkdown>
              </ChatBubble>
              <br />
            {messages.map((message, index) => (
              <React.Fragment key={`message-${index}`}>
              <ChatBubble
                ariaLabel={`${message.role === 'user' ? 'User' : 'Assistant'} message`}
                type={message.role === "user" ? "outgoing" : "incoming"}
                avatar={
                  message.role === "user" ? (
                  <Avatar
                    ariaLabel="Me"
                    tooltipText="Me"
                    initials="Me"
                  />) : (
                    <Avatar
                      color="gen-ai"
                      iconName="gen-ai"
                      ariaLabel="Generative AI assistant"
                      tooltipText="Generative AI assistant"
                    />
                  )
                }
              >
                <ReactMarkdown
                  key={`message-${index}`}
                  components={{
                    code: ({node, className, children, ...props}) => {
                      const match = /language-(\w+)/.exec(className || '');
                      const language = match && match[1];
                      
                      if (language === 'jsx') {
                        return (
                          <div>
                            <pre style={{ backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '5px', overflow: 'auto' }}>
                              <CodeView content={String(children).replace(/\n$/, '')} highlight={javascriptHighlight}/>
                            </pre>
                            <Button 
                              onClick={() => {
                                const codeContent = String(children).replace(/\n$/, '');
                                setCode(codeContent);
                              }}
                              variant="primary"
                            >
                              Apply
                            </Button>
                          </div>
                        );
                      }

                      else if (language === 'json') {
                        const formatJSON = (jsonString: string) => {
                          try {
                            const parsed = JSON.parse(jsonString);
                            return JSON.stringify(parsed, null, 2);
                          } catch (e) {
                            return jsonString;
                          }
                        };
                        
                        return <ExpandableSection headerText="details">
                          <pre style={{ backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '5px', overflow: 'auto' }}>
                            {formatJSON(String(children).replace(/\n$/, ''))}
                          </pre>
                        </ExpandableSection>
                      }
                      return <code className={className} {...props}>{children}</code>
                    },
                  }}
                >
                  {message.content[0].text}
                </ReactMarkdown>
                {(messages.length-1 === index && loading && message.role === "assistant") && <Spinner />}
              </ChatBubble>
              <br />
              </React.Fragment>
            ))}
          </div>
          
          <div>
            <PromptInput
              onChange={({ detail }) => setPrompt(detail.value)}
              onAction={async ({ detail }) => {
                if(loading) return;
                
                setLoading(true)
                
                await chat(detail.value);
                setPrompt("");

                setLoading(false)
              }}
              value={prompt}
              disabled={loading}
              actionButtonAriaLabel="Send message"
              actionButtonIconName="send"
              ariaLabel="Prompt input with min and max rows"
              maxRows={8}
              minRows={3}
              placeholder="Ask a question"
            />
          </div>
        </Box>
        
        <SandpackProvider
          template='react'
          customSetup={{
            dependencies: {
              "recharts": "latest",
              "react-is": "latest"
            }
          }}
          files={{
            "/App.js": code
          }}>
          <SandpackLayout >
            <SandpackPreview 
              style={{
                height: "90vh"
              }}
            />
          </SandpackLayout>
        </SandpackProvider>
      </Grid>
    </div>
  )
}

export default App
