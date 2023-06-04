const voiceTalking = {};

voiceTalking.parametersSettings = function () {
    let parameters = {};
    parameters.lang = 'en-US';
    parameters.phrases = {};
    parameters.phrases.startPhrases = {};
    parameters.phrases.executePhrases = {};
    parameters.phrases.switchPhrases = {};
    parameters.phrases.breakPhrases = {};
    parameters.phrases.responsePhrases = {};
    parameters.phrases.confirmPhrases = {};
    parameters.elements = {};
    parameters.elements.langTextElement = {};
    parameters.elements.statusTextElement = {};
    parameters.elements.inputElement = {};
    parameters.execMethod = '';
    parameters.defaultVoices = {};
    return parameters
}

//проверики наличия языков во фразах потом прикручу
voiceTalking.initializeTalkingFunctions = function (parameters) {
    //потом присобачить проверку наличия распознавания речи в браузере
    for (let _parameter in parameters) console.log(_parameter, parameters[_parameter]);
    for (let phraseSet in parameters.phrases) {
        voiceTalking._setPhrases(phraseSet, parameters.phrases[phraseSet]);
    }
    //тут по идее можно одним объектом обойтись, если переводить его в разные состояния
    //согласно кодовым фразам. оптимизировать этот момент потом
    voiceTalking.listener = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    voiceTalking.recognizer = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    voiceTalking.langTextElement = parameters.elements.langTextElement;
    voiceTalking.statusTextElement = parameters.elements.statusTextElement;
    //здесь подумать, как поправить установку языка по-умолчанию для синтеза речи
    voiceTalking.setLang(parameters.lang);
    voiceTalking.inputElement = parameters.elements.inputElement;
    voiceTalking.execMethod = parameters.execMethod;
    voiceTalking.listening = true;
    voiceTalking.recognizing = false;
    voiceTalking.defaultVoices = parameters.defaultVoices;
    voiceTalking._addSettingsButton(parameters);
    voiceTalking._initializeListening();
    voiceTalking._initializeRecognizing();
    voiceTalking._initializeSynthesis();
    voiceTalking._addSwithces();
}

voiceTalking._addSwithces = function() {
    voiceTalking.langTextElement.style.cursor = 'pointer';
    voiceTalking.langTextElement.addEventListener('click', function() {
        let nextLang = voiceTalking._getNextKey(voiceTalking.startPhrases, voiceTalking.lang);
        voiceTalking.setLang(nextLang, voiceTalking._synthesisCheckbox.checked);
    });
    voiceTalking.statusTextElement.style.cursor = 'pointer';
    voiceTalking.statusTextElement.addEventListener('click', function() {
        if (voiceTalking._recognitionCheckbox.checked) {
            if (voiceTalking.recognizing) {
                voiceTalking.inputElement.value = '';
                voiceTalking.stopRecognizing();
            } else if (voiceTalking.listening) {
                voiceTalking.listening = false;
                voiceTalking._startRecognizing();
            } else {
                voiceTalking.startListening();
            }
        }
    });
}

voiceTalking._getNextKey = function(object, current_key) {
  let keys = Object.keys(object);
  let currentIndex = keys.indexOf(current_key);
  let nextIndex = (currentIndex + 1) % keys.length;
  return keys[nextIndex];
}

voiceTalking.startListening = function () {
    console.log('start listening');
    voiceTalking.listening = true;
    voiceTalking.recognizing = false;
    voiceTalking.statusTextElement.textContent = 'listening...';
    voiceTalking.listener.start();
}

voiceTalking.stopListening = function () {
    if (voiceTalking.listening) {
        voiceTalking.listening = false;
        voiceTalking.listener.stop();
    }
}

voiceTalking.stopRecognizing = function () {
    if (voiceTalking.recognizing) {
        voiceTalking.recognizing = false;
        voiceTalking.recognizer.stop();
    }
}

voiceTalking.stopVoiceInput = function() {
   console.log('Stop voice input');
   voiceTalking.stopListening();
   voiceTalking.stopRecognizing();
   voiceTalking.statusTextElement.textContent = 'No voice input';
}

voiceTalking.synthesiseSpeech = function (text, onendMethod = null) {
    if (voiceTalking._synthesisCheckbox.checked) {
        responsiveVoice.speak(text, voiceTalking.voiceSelect.value,
            {lang: voiceTalking.lang, onend: onendMethod});
    } else if (onendMethod !== null) {
        onendMethod();
    }
}

voiceTalking.setLang = function (lang, switchSynthesis = false) {
    console.log('switching language to ' + lang);
    voiceTalking.lang = lang;
    voiceTalking.listener.lang = lang;
    voiceTalking.recognizer.lang = lang;
    voiceTalking.langTextElement.textContent = lang;
    if (switchSynthesis) voiceTalking.voiceSelect.value = voiceTalking.defaultVoices[lang];
}

voiceTalking._addSettingsButton = function (parameters) {
    let button = document.createElement('button');
    button.id = 'settings-button';
    button.style.backgroundColor = 'transparent';
    button.style.border = 'none';
    button.style.cursor = 'pointer';
    button.style.padding = '0';
    //потом поправить так, чтобы работало относительно того, где и как расположен сам проект,
    //а не прямо в лоб
    button.style.backgroundImage = 'url(/static/img/voice-recognition-settings.png)';
    button.style.width = '32px';
    button.style.height = '32px';
    button.style.backgroundSize = 'cover';
    button.style.backgroundPosition = 'center';
    button.style.top = '0';
    button.style.left = '0';
    button.style.zIndex = '9999';
    button.style.position = 'fixed';
    button.title = 'Voice recognition settings';
    button.onclick = voiceTalking._ShowHideSettings;
    //потом декомпозировать метод и поработать над внешним видом окна настроек
    voiceTalking._settingsWindow = document.createElement('div');
    voiceTalking._settingsWindow.style.position = 'fixed';
    voiceTalking._settingsWindow.style.top = '32px';
    voiceTalking._settingsWindow.style.backgroundColor = 'antiquewhite';
    voiceTalking._settingsWindow.style.left = '0';
    voiceTalking._settingsWindow.style.zIndex = '9998';
    voiceTalking._settingsWindow.style.display = 'none';
    //отрефакторить настройки в 2.0
    voiceTalking._addRecognitionSettings(parameters);
    document.body.appendChild(button);
    document.body.appendChild(voiceTalking._settingsWindow);
    voiceTalking._addSettingsCloseEvent();
}

voiceTalking._addSettingsCloseEvent = function () {
    document.addEventListener('click', function(event) {
        if (event.target !== voiceTalking._settingsWindow && !voiceTalking._settingsWindow.contains(event.target)
                && event.target !== document.getElementById('settings-button')) {
            voiceTalking._settingsWindow.style.display = 'none';
        }
    });
}

voiceTalking._addRecognitionSettings = function(parameters) {
    voiceTalking._addSettingsTitle('Voice recognition settings:');
    voiceTalking._addRecognitionCheckbox();
    for (let phrases in parameters.phrases) {
        let settingsDescription = document.createElement('p');
        settingsDescription.textContent = phrases + ': ' + JSON.stringify(parameters.phrases[phrases]);
        voiceTalking._settingsWindow.appendChild(settingsDescription);
    }
}

voiceTalking._addRecognitionCheckbox = function () {
    let label = document.createElement('label');
    label.for = 'recoginition-checkbox';
    label.textContent = 'Use voice recognition:';
    voiceTalking._recognitionCheckbox = document.createElement('input');
    voiceTalking._recognitionCheckbox.type = 'checkbox';
    voiceTalking._recognitionCheckbox.id = 'recoginition-checkbox';
    voiceTalking._recognitionCheckbox.onchange = voiceTalking._RecognitionCheckboxOnchange;
    voiceTalking._recognitionCheckbox.checked = true;
    voiceTalking._settingsWindow.appendChild(label);
    voiceTalking._settingsWindow.appendChild(voiceTalking._recognitionCheckbox);
}

voiceTalking._RecognitionCheckboxOnchange = function() {
    if (voiceTalking._recognitionCheckbox.checked) {
        voiceTalking.startListening();
    } else {
        voiceTalking.stopVoiceInput();
    }
}

voiceTalking._addSettingsTitle = function (text) {
    let settingsTitle = document.createElement('p');
    settingsTitle.style.color = 'blue';
    settingsTitle.textContent = text;
    voiceTalking._settingsWindow.appendChild(settingsTitle);
}

voiceTalking._ShowHideSettings = function () {
    if (voiceTalking._settingsWindow.style.display === 'none') {
        voiceTalking._settingsWindow.style.display = 'block';
    } else {
        voiceTalking._settingsWindow.style.display = 'none';
    }
}

voiceTalking._initializeListening = function () {
    voiceTalking.listener.addEventListener('result', (_event) => {
        let result = _event.results[_event.results.length - 1][0].transcript.toLowerCase().trim();
        console.log('voice listening result: ' + result);
        let switchPhrases = voiceTalking.switchPhrases[voiceTalking.lang]
        if (result in switchPhrases) {
            voiceTalking.listening = true;
            voiceTalking.synthesiseSpeech(voiceTalking.confirmPhrases[voiceTalking.lang],
                function () {voiceTalking.setLang(switchPhrases[result], true)});
        } else if (result === voiceTalking.startPhrases[voiceTalking.lang]) {
            voiceTalking.listening = false;
            voiceTalking.synthesiseSpeech(voiceTalking.responsePhrases[voiceTalking.lang],
                voiceTalking._startRecognizing);
        }
    });
    voiceTalking.listener.addEventListener('end', () => {
        if (voiceTalking.listening) {
            console.log('restart listening');
            voiceTalking.startListening();
        }
    });
}

voiceTalking._startRecognizing = function () {
    console.log('start recognizing');
    voiceTalking.recognizing = true;
    voiceTalking.statusTextElement.textContent = 'recognizing...';
    voiceTalking.recognizer.start();
}

voiceTalking._initializeRecognizing = function () {
    voiceTalking.recognizer.addEventListener('result', (_event) => {
        let result = _event.results[_event.results.length - 1][0].transcript.toLowerCase().trim();
        console.log('voice recognizing result: ' + result);
        if (result === voiceTalking.executePhrases[voiceTalking.lang]) {
            console.log('executing method');
            voiceTalking.listening = true;
            voiceTalking.recognizing = false;
            //здесь бы надо блокировать распознавание речи, пока идет её синтез
            voiceTalking.synthesiseSpeech(voiceTalking.confirmPhrases[voiceTalking.lang],
                voiceTalking.execMethod);
        } else if (result === voiceTalking.breakPhrases[voiceTalking.lang]) {
            voiceTalking.inputElement.value = '';
            voiceTalking.listening = true;
            voiceTalking.recognizing = false;
            voiceTalking.synthesiseSpeech(voiceTalking.confirmPhrases[voiceTalking.lang]);
        } else {
            console.log('adding recognition result');
            voiceTalking.inputElement.value += result + ' ';
            voiceTalking.inputElement.scrollTop = voiceTalking.inputElement.scrollHeight;
            voiceTalking.recognizing = true;
        }
    });

    voiceTalking.recognizer.addEventListener('end', () => {
        //повесить на отдельное от флага свойство?
        if (voiceTalking._recognitionCheckbox.checked) {
            if (voiceTalking.recognizing) {
                voiceTalking._startRecognizing();
            } else {
                voiceTalking.startListening();
            }
        }
    });
}

voiceTalking._setPhrases = function (propertyName, phrases) {
    console.log('establishing speech recognition ' + propertyName);
    voiceTalking[propertyName] = {};
    for (let lang in phrases) {
        console.log('language: ' + lang);
        if (propertyName === 'switchPhrases') {
            voiceTalking[propertyName][lang] = {};
            for (let phrase in phrases[lang]) {
                voiceTalking[propertyName][lang][phrase.toLowerCase().trim()] = phrases[lang][phrase];
                console.log(phrase.toLowerCase().trim() + ': ' + phrases[lang][phrase]);
            }
        } else {
            voiceTalking[propertyName][lang] = phrases[lang].toLowerCase().trim();
            console.log(phrases[lang].toLowerCase().trim());
        }
    }
}

voiceTalking._initializeSynthesis = function () {
    let script = document.createElement('script');
    script.src = 'https://code.responsivevoice.org/responsivevoice.js';
    script.onload = voiceTalking._addSynthesisSettings;
    document.head.appendChild(script);
}

voiceTalking._addSynthesisSettings = function () {
    voiceTalking._addSettingsTitle('Voice synthesis settings:');
    voiceTalking._addDefaultVoices();
    voiceTalking._addSynthesisCheckbox();
    voiceTalking._settingsWindow.appendChild(document.createElement('p'));
    voiceTalking._addVoicesList();
}

voiceTalking._addDefaultVoices = function () {
    let defaultVoices = document.createElement('p');
    defaultVoices.textContent = 'Default voices: ' + JSON.stringify(voiceTalking.defaultVoices);
    voiceTalking._settingsWindow.appendChild(defaultVoices);
}

voiceTalking._addSynthesisCheckbox = function () {
    let label = document.createElement('label');
    label.for = 'synthesis-checkbox';
    label.textContent = 'Use voice synthesis:';
    voiceTalking._synthesisCheckbox = document.createElement('input');
    voiceTalking._synthesisCheckbox.type = 'checkbox';
    voiceTalking._synthesisCheckbox.id = 'synthesis-checkbox';
    voiceTalking._synthesisCheckbox.onchange = voiceTalking._SynthesisCheckboxOnchange;
    voiceTalking._synthesisCheckbox.checked = true;
    voiceTalking._settingsWindow.appendChild(label);
    voiceTalking._settingsWindow.appendChild(voiceTalking._synthesisCheckbox);
}

voiceTalking._SynthesisCheckboxOnchange = function () {
    voiceTalking.voiceSelect.disabled = !voiceTalking._synthesisCheckbox.checked;
}

voiceTalking._addVoicesList = function () {
    let label = document.createElement('label');
    label.for = 'voice-select';
    label.textContent = 'Voice:';
    voiceTalking.voiceSelect = document.createElement('select');
    voiceTalking.voiceSelect.id = 'voice-select';
    for (let voice of responsiveVoice.getVoices()) {
        let voiceOption = document.createElement('option');
        voiceOption.value = voice.name;
        voiceOption.textContent = voice.name;
        voiceTalking.voiceSelect.appendChild(voiceOption);
    }
    voiceTalking.voiceSelect.value = voiceTalking.defaultVoices[voiceTalking.lang];
    voiceTalking._settingsWindow.appendChild(label);
    voiceTalking._settingsWindow.appendChild(voiceTalking.voiceSelect);
}