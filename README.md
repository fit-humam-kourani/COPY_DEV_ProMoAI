# ProMoAI
ProMoAI is a Streamlit app that leverages Large Language Models (LLMs) from major AI providers for the automatic generation and redesign of process models. The tool offers multiple entry points for creating and improving process models:
* ***Text:*** Start with a textual description of your process, and ProMoAI will generate an initial process model. You can iteratively improve and refine the process model by providing feedback.
* ***Model:*** Import an existing process model to further refine and enhance it using ProMoAI.
* ***Data:*** Provide an event log to perform process discovery, generating an initial process model. This model can then be redesigned and improved using ProMoAI.

The generated process models can be exported in BPMN and PNML formats.

## Launching the App
You have two options for running ProMoAI.
* ***On the cloud:*** under https://promoai.streamlit.app/.
* ***Locally:*** by cloning this repository, installing the required environment and packages, and then running 'streamlit run app.py'.


## Requirements

* *Environment:* the app is tested on both Python 3.9 and 3.10.
* *Dependencies:* all required dependencies are listed in the file 'requirements.txt'.
* *Packages:* all required packages are listed in the file 'packages.txt'.
