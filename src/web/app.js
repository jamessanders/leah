const App = () => {
    // Load initial state from localStorage or use defaults
    const [inputValue, setInputValue] = React.useState('');
    const [responses, setResponses] = React.useState(() => {
        const saved = localStorage.getItem('responses');
        return saved ? JSON.parse(saved) : [];
    });
    const [loading, setLoading] = React.useState(false);
    const [personas, setPersonas] = React.useState([]);
    const [selectedPersona, setSelectedPersona] = React.useState(() => {
        return localStorage.getItem('selectedPersona') || 'leah';
    });
    const inputRef = React.useRef(null);
    const responseAreaRef = React.useRef(null);
    const audioRef = React.useRef(null);
    const [conversationHistory, setConversationHistory] = React.useState(() => {
        const saved = localStorage.getItem('conversationHistory');
        return saved ? JSON.parse(saved) : [];
    });
    const [audioQueue, setAudioQueue] = React.useState([]);
    const [queue, setQueue] = React.useState([]);
    const [isPlaying, setIsPlaying] = React.useState(false);
    const [isMobile, setIsMobile] = React.useState(false);
    const [isModalOpen, setIsModalOpen] = React.useState(false);
    const [modalInputValue, setModalInputValue] = React.useState('');
    const [submissionQueue, setSubmissionQueue] = React.useState([]);

    const userAvatarUrl = 'https://via.placeholder.com/40?text=U'; // Placeholder for user avatar
    const assistantAvatarUrl = `/avatars/avatar-${selectedPersona}.png`;

    // Save state to localStorage whenever it changes
    React.useEffect(() => {
        localStorage.setItem('responses', JSON.stringify(responses));
    }, [responses]);

    React.useEffect(() => {
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    }, [conversationHistory]);

    React.useEffect(() => {
        localStorage.setItem('selectedPersona', selectedPersona);
    }, [selectedPersona]);

    // Fetch available personas on component mount
    React.useEffect(() => {
        const fetchPersonas = async () => {
            try {
                const response = await fetch('/personas');
                const data = await response.json();
                setPersonas(data);
            } catch (error) {
                console.error('Error fetching personas:', error);
            }
        };
        fetchPersonas();
    }, []);

    const handlePersonaChange = (event) => {
        setSelectedPersona(event.target.value);
    };

    const handleInputChange = (event) => {
        setInputValue(event.target.value);
    };

    const handleKeyPress = (event) => {
        if (event.key === 'Enter') {
            handleSubmit(event.target.value);
        }
    };

    const handleBlur = () => {
        // On mobile, when keyboard is dismissed (blur event), submit if there's text
        if (isMobile && inputValue.trim() !== '') {
            handleSubmit();
        }
    };

    const processNextSubmission = React.useCallback(() => {
        console.log("Attempting to process next submission");
        console.log("Current queue:", submissionQueue);
        if (submissionQueue.length > 0) {
            const nextSubmission = submissionQueue[0];
            console.log("Processing submission:", nextSubmission);
            setSubmissionQueue(submissionQueue.slice(1));
            handleSubmit(nextSubmission);
        } else {
            console.log("No submissions to process");
        }
    }, [submissionQueue]);

    const handleSubmit = async (input = inputValue) => {
        if (loading) {
            setSubmissionQueue(prevQueue => [...prevQueue, input]);
            console.log("Currently loading, queuing submission:", input);
            setInputValue(''); // Clear the input field immediately when queuing
            console.log("Updated submission queue (after queuing):", submissionQueue);
            return;
        }

        console.log("Submitting input:", input);
        try {
            setLoading(true); // Show loading message
            const updatedHistory = [...conversationHistory, { role: 'user', content: input }];
            setConversationHistory(updatedHistory);
            setResponses([...responses, { role: 'user', content: input }]);
            setInputValue(''); // Clear the input field before submitting
            setModalInputValue('');

            const res = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    query: input, 
                    history: updatedHistory,
                    persona: selectedPersona,
                    context: modalInputValue // Pass modal input value as context
                }),
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');

            let assistantResponse = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });

                // Split the chunk into individual JSON objects
                const jsonObjects = chunk.split('\n\n').filter(Boolean);
                for (const jsonObject of jsonObjects) {
                    try {
                        // Strip the 'data:' prefix and parse the JSON response
                        const jsonResponse = JSON.parse(jsonObject.replace(/^data:\s*/, ''));

                        if (jsonResponse.type === 'system' && jsonResponse.content) {
                            console.log('System message:', jsonResponse.content);
                        } else if (jsonResponse.type === 'end') {
                            setLoading(false); // Hide loading message
                            console.log("Finished processing submission, checking queue");
                            console.log("DONE Submission queue:", submissionQueue);
                            processNextSubmission(); // Process the next submission in the queue
                        } else if (jsonResponse.content) {
                            // Append content as plain text
                            const plainTextContent = jsonResponse.content;
                            assistantResponse += plainTextContent;
                            setResponses(prevResponses => {
                                const lastResponse = prevResponses[prevResponses.length - 1];
                                if (lastResponse.role === 'assistant') {
                                    // Append to the last assistant response
                                    lastResponse.content += plainTextContent;
                                    return [...prevResponses.slice(0, -1), lastResponse];
                                } else {
                                    // Add a new assistant response
                                    return [...prevResponses, { role: 'assistant', content: plainTextContent }];
                                }
                            });
                        } else if (jsonResponse.voice_type && jsonResponse.filename) {
                            addToAudioQueue("/voice/" + jsonResponse.filename); // Add to the audio queue
                        } else if (jsonResponse.type === "history" && jsonResponse.history) {
                            // Update the conversation history with the server's version
                            setConversationHistory(jsonResponse.history);
                        } 
                    } catch (error) {
                        console.error('Error parsing JSON:', error);
                    }
                }
            }

            // Store the complete assistant response in conversation history
            setConversationHistory(prevHistory => [...prevHistory, { role: 'assistant', content: assistantResponse }]);

            // Convert the complete response from markdown to HTML
            const htmlResponse = marked.parse(assistantResponse);

            // Overwrite the UI with the converted HTML content
            setResponses(prevResponses => {
                // Filter out system messages
                const filteredResponses = prevResponses.filter(response => !response.content.includes('<i>System:'));
                const lastResponse = filteredResponses[filteredResponses.length - 1];
                if (lastResponse && lastResponse.role === 'assistant') {
                    // Overwrite the last assistant response
                    lastResponse.content = htmlResponse;
                    return [...filteredResponses.slice(0, -1), lastResponse];
                } else {
                    // Add a new assistant response
                    return [...filteredResponses, { role: 'assistant', content: htmlResponse }];
                }
            });
        }    catch (error) {
            console.error('Error:', error);
        } 
    };

    const useAudioPlayer = () => {
        // We are managing promises of audio urls instead of directly storing strings
        // because there is no guarantee when openai tts api finishes processing and resolves a specific url
        // For more info, check this comment:
        // https://github.com/tarasglek/chatcraft.org/pull/357#discussion_r1473470003
        const [queue, setQueue] = React.useState([]);
        const [isPlaying, setIsPlaying] = React.useState(false);
      
        React.useEffect(() => {
          if (!isPlaying && queue.length > 0) {
            playAudio(queue[0]);
          }
        }, [queue, isPlaying]);
      
        const playAudio = async (audioClipUri) => {
          console.log('Attempting to play audio with Web Audio API:', audioClipUri);
          if (!audioClipUri) {
              console.error('No audio URI provided');
              return;
          }
          setIsPlaying(true);
          const audioUrl = await audioClipUri;
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          try {
              const response = await fetch(audioUrl);
              const arrayBuffer = await response.arrayBuffer();
              const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
              const source = audioContext.createBufferSource();
              source.buffer = audioBuffer;
              source.connect(audioContext.destination);
              source.onended = () => {
                  setQueue((oldQueue) => oldQueue.slice(1));
                  setIsPlaying(false);
                  audioContext.close();
              };
              source.start(0);
          } catch (error) {
              console.error('Error with Web Audio API playback:', error);
              setIsPlaying(false);
              audioContext.close();
          }
        };
      
        const addToAudioQueue = (audioClipUri) => {
          setQueue((oldQueue) => [...oldQueue, audioClipUri]);
        };
      
        return { addToAudioQueue };
      };
      const { addToAudioQueue } = useAudioPlayer()

    React.useEffect(() => {
        if (inputRef.current) {
            inputRef.current.focus();
        }
    }, []);

    React.useEffect(() => {
        if (responseAreaRef.current) {
            responseAreaRef.current.scrollTop = responseAreaRef.current.scrollHeight;
        }
    }, [responses]);

    // Detect if the device is mobile
    React.useEffect(() => {
        const checkIfMobile = () => {
            const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            setIsMobile(isMobileDevice);
        };
        
        checkIfMobile();
        window.addEventListener('resize', checkIfMobile);
        
        return () => {
            window.removeEventListener('resize', checkIfMobile);
        };
    }, []);

    const handleModalOpen = () => {
        setIsModalOpen(true);
    };

    const handleModalClose = () => {
        setIsModalOpen(false);
    };

    const handleModalInputChange = (event) => {
        setModalInputValue(event.target.value);
    };

    return React.createElement('div', null,
        React.createElement('div', { className: 'header' },
            React.createElement('h1', null, ''),
            React.createElement('select', {
                className: 'personaSelector',
                value: selectedPersona,
                onChange: handlePersonaChange
            },
                personas.map(persona =>
                    React.createElement('option', {
                        key: persona,
                        value: persona
                    }, persona.charAt(0).toUpperCase() + persona.slice(1))
                )
            ),
            React.createElement('div', {
                onClick: () => {
                    console.log("Resetting conversation history");
                    // Clear conversation history when changing personas
                    setConversationHistory([]);
                    setResponses([]);
                    // Clear localStorage for conversation history
                    localStorage.removeItem('conversationHistory');
                    localStorage.removeItem('responses');
                },
                className: 'resetButton',
                style: { display: 'inline-block', padding: '10px 20px', fontSize: '16px', cursor: 'pointer', backgroundColor: '#007BFF', color: 'white', border: 'none', borderRadius: '5px', marginLeft: '10px' }
            }, 'Reset'),
            React.createElement('div', { onClick: handleModalOpen, className: 'open-modal', style: { marginLeft: '10px' } }, 'Context')
        ),
        React.createElement('div', { className: 'responseArea', ref: responseAreaRef },
            responses.map((item, index) =>
                React.createElement('div', {
                    key: index,
                    className: item.role === 'user' ? 'userInputBox' : 'responseBox',
                    style: { display: 'flex', alignItems: 'flex-start' } // Align items vertically at the start
                },
                React.createElement('div', {
                    className: 'avatar' // Assign class name 'avatar'
                },
                item.role === 'assistant' && React.createElement('img', {
                    src: assistantAvatarUrl,
                    alt: 'Assistant Avatar'
                })),
                React.createElement('div', {
                    className: 'content', // Assign class name 'content'
                    dangerouslySetInnerHTML: { __html: item.content }
                })
            )),
            loading && React.createElement('div', { className: 'loadingMessage' }, 'Thinking...')
        ),
        React.createElement('input', {
            type: 'text',
            value: inputValue,
            onChange: handleInputChange,
            onKeyPress: handleKeyPress,
            onBlur: handleBlur,
            placeholder: 'Enter your query',
            className: 'queryInput',
            ref: inputRef
        }),
        isModalOpen && (
            React.createElement('div', { className: 'modal' },
                React.createElement('textarea', {
                    value: modalInputValue,
                    onChange: handleModalInputChange,
                    placeholder: 'Enter your context here...'
                }),
                React.createElement('div', { onClick: handleModalClose, className: 'close-modal', style: { cursor: 'pointer', padding: '10px 20px', backgroundColor: '#007bff', color: '#fff', borderRadius: '5px', display: 'inline-block', textAlign: 'center', marginTop: '10px' } }, 'Close')
            )
        )
    );
};

ReactDOM.render(React.createElement(App), document.getElementById('root')); 