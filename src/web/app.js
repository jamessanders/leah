const App = () => {
    const [inputValue, setInputValue] = React.useState('');
    const [responses, setResponses] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const inputRef = React.useRef(null);
    const responseAreaRef = React.useRef(null);
    const audioRef = React.useRef(null);
    const [conversationHistory, setConversationHistory] = React.useState([]);
    const [audioQueue, setAudioQueue] = React.useState([]);
    const [queue, setQueue] = React.useState([]);
    const [isPlaying, setIsPlaying] = React.useState(false);

    const handleInputChange = (event) => {
        setInputValue(event.target.value);
    };

    const handleKeyPress = (event) => {
        if (event.key === 'Enter') {
            handleSubmit();
        }
    };

    const handleSubmit = async () => {
        try {
            setLoading(true); // Show loading message
            const updatedHistory = [...conversationHistory, { role: 'user', content: inputValue }];
            setConversationHistory(updatedHistory);
            setResponses([...responses, { role: 'user', content: inputValue }]);
            setInputValue(''); // Clear the input field before submitting

            const res = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: inputValue, history: updatedHistory }),
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');

            let assistantResponse = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                console.log(chunk);

                // Split the chunk into individual JSON objects
                const jsonObjects = chunk.split('\n\n').filter(Boolean);
                for (const jsonObject of jsonObjects) {
                    try {
                        // Strip the 'data:' prefix and parse the JSON response
                        const jsonResponse = JSON.parse(jsonObject.replace(/^data:\s*/, ''));
                        console.log(jsonResponse);

                        if (jsonResponse.content) {
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
                        }
                    } catch (error) {
                        console.log(jsonObject);
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
                const lastResponse = prevResponses[prevResponses.length - 1];
                if (lastResponse.role === 'assistant') {
                    // Overwrite the last assistant response
                    lastResponse.content = htmlResponse.replace(/\n/g, '<br/>');
                    return [...prevResponses.slice(0, -1), lastResponse];
                } else {
                    // Add a new assistant response
                    return [...prevResponses, { role: 'assistant', content: htmlResponse }];
                }
            });
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false); // Hide loading message
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
          setIsPlaying(true);
          const audioUrl = await audioClipUri;
          const audio = new Audio(audioUrl);
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl); // To avoid memory leaks
            setQueue((oldQueue) => oldQueue.slice(1));
            setIsPlaying(false);
          };
          audio.play();
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

    
    return React.createElement('div', null,
        React.createElement('div', { className: 'responseArea', ref: responseAreaRef },
            responses.map((item, index) =>
                React.createElement('div', {
                    key: index,
                    className: item.role === 'user' ? 'userInputBox' : 'responseBox',
                    dangerouslySetInnerHTML: { __html: item.content }
                })
            ),
            loading && React.createElement('div', { className: 'loadingMessage' }, 'Loading...')
        ),
        React.createElement('input', {
            type: 'text',
            value: inputValue,
            onChange: handleInputChange,
            onKeyPress: handleKeyPress,
            placeholder: 'Enter your query',
            className: 'queryInput',
            ref: inputRef
        })
    );
};

ReactDOM.render(React.createElement(App), document.getElementById('root')); 