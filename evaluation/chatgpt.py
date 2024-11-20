import os
import socket
import threading
import time

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

chrome_driver_path = r"C:\programs\chromedriver-win64\chromedriver-win64\chromedriver.exe"
chrome_path = r"C:\programs\chrome-win64\chrome-win64\chrome.exe"


class ChatGPTAutomation:

    def __init__(self, model):
        """
        This constructor automates the following steps:
        1. Open a Chrome browser with remote debugging enabled at a specified URL.
        2. Prompt the user to complete the log-in/registration/human verification, if required.
        3. Connect a Selenium WebDriver to the browser instance after human verification is completed.

        :param chrome_path: file path to chrome.exe (ex. C:\\Users\\User\\...\\chromedriver.exe)
        :param chrome_driver_path: file path to chromedriver.exe (ex. C:\\Users\\User\\...\\chromedriver.exe)
        """

        self.chrome_path = chrome_path
        self.chrome_driver_path = chrome_driver_path
        self.model = model
        self.url = f"https://chat.openai.com?model={model}"
        free_port = self.find_available_port()
        self.launch_chrome_with_remote_debugging(free_port, self.url)
        self.wait_for_human_verification()
        self.driver = self.setup_webdriver(free_port)
        self.cookie = self.get_cookie()

    @staticmethod
    def find_available_port():
        """ This function finds and returns an available port number on the local machine by creating a temporary
            socket, binding it to an ephemeral port, and then closing the socket. """

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def launch_chrome_with_remote_debugging(self, port, url):
        """ Launches a new Chrome instance with remote debugging enabled on the specified port and navigates to the
            provided url """

        def open_chrome():
            chrome_cmd = f"{self.chrome_path} --remote-debugging-port={port} --user-data-dir=remote-profile {url}"
            os.system(chrome_cmd)

        chrome_thread = threading.Thread(target=open_chrome)
        chrome_thread.start()

    def setup_webdriver(self, port):
        """  Initializes a Selenium WebDriver instance, connected to an existing Chrome browser
             with remote debugging enabled on the specified port"""

        # chrome_options = webdriver.ChromeOptions()
        # chrome_options.binary_location = self.chrome_driver_path
        # chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        # driver = webdriver.Chrome(options=chrome_options)
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = self.chrome_driver_path
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        service = Service(executable_path=self.chrome_driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        return self.driver

    def get_cookie(self):
        """
        Get chat.openai.com cookie from the running chrome instance.
        """
        cookies = self.driver.get_cookies()
        cookie = [elem for elem in cookies if elem["name"] == '__Secure-next-auth.session-token'][0]['value']
        return cookie

    def send_prompt_to_chatgpt(self, prompt):
        """ Sends a message to ChatGPT and waits for 20 seconds for the response """

        input_box = self.driver.find_element(By.ID, "prompt-textarea")
        self.driver.execute_script("arguments[0].innerHTML = '<p>' + arguments[1] + '</p>';", input_box, prompt)
        input_box.send_keys(Keys.RETURN)
        self.check_response_started()
        self.check_response_ended()

    def check_response_started(self):
        """ Checks if ChatGPT response started """
        while True:
            try:
                self.driver.find_element(By.CSS_SELECTOR,
                                         'button[aria-label="Stop streaming"][data-testid="stop-button"]')
                print("ChatGPT response started")
                return
            except NoSuchElementException:
                time.sleep(1)

    def check_response_ended(self):
        """ Checks if ChatGPT response ended """
        while True:
            try:
                self.driver.find_element(By.CSS_SELECTOR,
                                         'button[aria-label="Send prompt"][data-testid="send-button"]')
                print("ChatGPT response ended")
                return
            except NoSuchElementException:
                time.sleep(1)

    def return_last_response(self):
        """ :return: the text of the last chatgpt response """
        time.sleep(5)
        divs = self.driver.find_elements(
            By.CSS_SELECTOR,
            'div[data-message-author-role="assistant"]'
        )

        if divs:
            last_div = divs[-1]
            return last_div
        else:
            raise Exception("No matching divs found.")

    @staticmethod
    def wait_for_human_verification():
        print("You need to manually complete the log-in or the human verification if required.")

        while True:
            user_input = input(
                "Enter 'y' if you have completed the log-in or the human verification, or 'n' to check again: ").lower().strip()

            if user_input == 'y':
                print("Continuing with the automation process...")
                break
            elif user_input == 'n':
                print("Waiting for you to complete the human verification...")
                time.sleep(5)  # You can adjust the waiting time as needed
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    def quit(self):
        """ Closes the browser and terminates the WebDriver session."""
        print("Closing the browser...")
        self.driver.close()
        self.driver.quit()

    def reload_page(self):
        """Reloads the current page by navigating back to the same URL."""
        self.driver.get(self.url)
        time.sleep(5)

# chatgpt = ChatGPTAutomation()
# for prompt in ['hi', 'bye']:
#     chatgpt.send_prompt_to_chatgpt(prompt)
#     response = chatgpt.return_last_response()
#     print(response)
#     chatgpt.send_prompt_to_chatgpt('ok')
#     response = chatgpt.return_last_response()
#     print(response)
#     chatgpt.reload_page()
# chatgpt.quit()
