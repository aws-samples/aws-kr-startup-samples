import { MutableRefObject, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom'
import QRCode from "react-qr-code";
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { TransitionGroup, CSSTransition } from 'react-transition-group';

import "./Display.css";

const endpoint = process.env.REACT_APP_API_ENDPOINT;

const queryClient = new QueryClient();

interface ImageElement {
  imageUrl: string;
  story: string;
  uuid: string;
};

const DisplayApp = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <DisplayComponent />
    </QueryClientProvider>
  );
}

const DisplayComponent = () => {

  const { id } = useParams<{ id: string }>();
  const [ uuid, setUuid ] = useState<string>("");
  const [ result, setResult ] = useState<ImageElement | null>(null);
  const [ imgState, setImgState ] = useState<number>(1);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const { data } = useQuery({
    queryKey: [id],
    queryFn: () =>
      fetch(`${endpoint}/images/${id}`).then((res) =>
        res.json()
      ),
    refetchInterval: 5000,
  });

  useEffect(() => {
    if(!data) return;
    const d: ImageElement = data as ImageElement;

    if (d.uuid !== uuid){
      setUuid(d.uuid);
      setImgState(-1);
      setResult(d);
    }
  }, [data, uuid]);

  useEffect(()=>{
    if(imgState === -1 && result){
      setImgState(2)
    }
  }, [result, imgState])


  const handleAudioEnd = () => {
    if(imgState < 2){
      setImgState((s) => (Math.min(s+1, 2)))
    }
  }

  if(!result) return;

  return (
      <div className='display-page' onClick={() => {
        if(imgState < 2){
          setImgState((s) => (Math.min(s+1, 2)))
          if(audioRef.current) {
            audioRef.current.pause();
          }
        }
      }}
      >
        <div className="display-container">
          <TransitionGroup className="display-transition-group">
            <CSSTransition
                key={imgState}
                timeout={10000}
                classNames={"display-page-transition"}
                unmountOnExit
                in={true}
            >
              <ImageComponent audioRef={audioRef} element={result} handleAudioEnd={handleAudioEnd}/>
            </CSSTransition>
                  
          </TransitionGroup>
        </div>
      </div>
  )
}

interface ImageComponentProps {
  audioRef:  MutableRefObject<HTMLAudioElement>
  element: ImageElement | null;
  handleAudioEnd: () => void;
}

const ImageComponent = ({audioRef, element, handleAudioEnd}: ImageComponentProps) => {

  const messages = {
    "bg1": "Let me explain your era. ",
    "bg2": "Let me explain your era. ",
    "bg3": "Let's experience what it would be like if you were in this era. ",
  };
  const [showMsg, setShowMsg] = useState(false);

  const cleanupAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = ''; // Clear the source
      audioRef.current.load(); // Force reload
      audioRef.current.remove();
      audioRef.current = null;
    }
  };

  // useEffect(() => {
  //   navigator.mediaDevices.getUserMedia({ audio: true })
  //   cleanupAudio();

  //   const msgTimer = setTimeout(() => {
  //     playMessge();
  //   }, 1000);

  //   return (() => {
  //     clearTimeout(msgTimer);
  //   })
  // }, [])

  const getAudio = async (text:string) => {

    const res = await fetch(`${endpoint}/speech`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        text: text
      })
    })
    const data = await res.json();
    return data;
  }

  // const playMessge = async () => {

  //   const text =  messages[element.type];
  //   const audioData = await getAudio(text);
  //   audioRef.current = new Audio("data:audio/mp3;base64," + audioData.audioContent);
  //   audioRef.current.loop = false;
  //   audioRef.current.onended = (event) => {
  //       playStory();
  //       setShowMsg(false);
  //   }
  //   audioRef.current.play();
  
  // }

  // const playStory = async () => {

  //   const text = element.story
  //   const audioData = await getAudio(text);
  //   audioRef.current = new Audio("data:audio/mp3;base64," + audioData.audioContent);
  //   audioRef.current.loop = false;
  //   audioRef.current.onended = (event) => {
  //       handleAudioEnd();
  //   }
  //   audioRef.current.play();
  
  //   }

  return(
    <div className='display-image-component'>

      {/* <div className={`display-message ${showMsg ? "" : "hidden"}`}>
        {messages[element.type]}
      </div> */}
      
      <div className="display-textbox">
        <div className="display-text">
            <span>
              {element.story}
            </span>
        </div>
      </div>
      <img className='display-image' src={element.imageUrl} alt="generative-gallery"/>
      {/* {element.type === "bg3" &&
      <div className="display-qr">
          <QRCode
              size={256}
              style={{ height: "100%", width: "100%", opacity: 0.5}}
              value={"https://d3cqhkimjbonxf.cloudfront.net" + element.image.split("?")[0].slice(45)}
              viewBox={`0 0 256 256`}
          />
      </div>
      } */}
    </div>
  );
};

export default DisplayApp;