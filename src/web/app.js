const App = () => {
    const [inputValue, setInputValue] = React.useState('');
    const [responses, setResponses] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const inputRef = React.useRef(null);
    const responseAreaRef = React.useRef(null);
    const audioRef = React.useRef(null);
    const [conversationHistory, setConversationHistory] = React.useState([]);

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
            // Update conversation history with the new user input
            const updatedHistory = [...conversationHistory, { role: 'user', content: inputValue }];
            setConversationHistory(updatedHistory);
            setResponses([...responses, { role: 'user', content: inputValue }]);
            setInputValue(''); // Clear the input field before submitting

            // Prepare the conversation history with role and content
            const res = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: inputValue, history: updatedHistory }),
            });
            const data = await res.json();
            // Update the local conversation history with the history from the response
            setConversationHistory(data.history);
            // Convert markdown response to HTML
            const htmlResponse = marked.parse(data.response);
            // Add new response to the list with role and content
            setResponses(prevResponses => [...prevResponses, { role: 'assistant', content: htmlResponse }]);

            // Stop previous audio if it exists
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.currentTime = 0;
            }

            // Play the new audio response
            const audio = new Audio(data.audio_url);
            audioRef.current = audio;
            audio.play();
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false); // Hide loading message
        }
    };

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