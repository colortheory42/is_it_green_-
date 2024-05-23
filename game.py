import pygame
import random
from pathlib import Path
from voice_interface import generate_speech, play_audio, record_audio, transcribe_audio_google_with_api_key, get_openai_response

# Initialize Pygame
pygame.init()

# Define colors
WHITE = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (30, 144, 255)
GREEN = (60, 179, 113)

# Define screen dimensions
SCREEN_WIDTH = 4480
SCREEN_HEIGHT = 2520

# Initialize screen in full screen mode
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("is this green?")

# Load sound effect
incorrect_sound = pygame.mixer.Sound("incorrect.wav")

# Define fonts
font = pygame.font.SysFont(None, 72, bold=True)

def generate_random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def is_green(color, red_tolerance=25, blue_tolerance=25, ratio_threshold=1.2):
    red_component = color[0]
    green_component = color[1]
    blue_component = color[2]

    # Ensure green is the highest component with some tolerance
    is_green_highest = green_component > red_component and green_component > blue_component

    # Adjusted tolerance for red and blue components
    red_within_tolerance = green_component - red_component > red_tolerance
    blue_within_tolerance = green_component - blue_component > blue_tolerance

    # Ratio checks to ensure green is dominant
    red_ratio = green_component / (red_component + 1)  # +1 to avoid division by zero
    blue_ratio = green_component / (blue_component + 1)  # +1 to avoid division by zero

    # Additional check for borderline cases
    borderline_green = (green_component > 100) and (red_component < 150) and (blue_component < 150)
    edge_case_green = (green_component > 90) and (green_component - red_component > 10) and (green_component - blue_component > 10)

    return (is_green_highest and red_within_tolerance and blue_within_tolerance and
            red_ratio > ratio_threshold and blue_ratio > ratio_threshold) or borderline_green or edge_case_green

def help_button_action():
    audio_file_path = Path(__file__).parent / "recorded_audio.wav"
    speech_file_path = Path(__file__).parent / "speech.mp3"

    try:
        # Step 1: Play the question
        question_text = "How can I help you?"
        generate_speech(question_text, speech_file_path)
        play_audio(speech_file_path)

        # Step 2: Record the user's response
        print("Recording for 10 seconds...")
        record_audio(audio_file_path, duration=5)
        print(f"Recording complete. Saved to {audio_file_path}")

        # Step 3: Transcribe the audio
        print(f"Transcribing audio from {audio_file_path}")
        transcription = transcribe_audio_google_with_api_key(audio_file_path)
        print("Transcription:", transcription)

        if not transcription:
            print("No transcription available. Please try recording again.")
        else:
            system_message = {
                "role": "system",
                "content": "You are my AI assistant."
            }

            user_message = {
                "role": "user",
                "content": transcription
            }

            # Step 4: Get the response from OpenAI
            assistant_response = get_openai_response([system_message, user_message])
            if not assistant_response:
                print("Failed to fetch a response from the model. Please check your API credentials or connectivity.")
            else:
                print("Assistant:", assistant_response)

                # Step 5: Generate and play the assistant's response
                generate_speech(assistant_response, speech_file_path)
                play_audio(speech_file_path)
    except Exception as e:
        print(f"An error occurred: {e}")



def main():
    pass_count = 0
    total_count = 0
    epoch = 1
    tolerance = 100  # Initial tolerance level

    clock = pygame.time.Clock()

    running = True
    while running:
        screen.fill(WHITE)

        # Generate random color
        color = generate_random_color()

        # Display color box
        pygame.draw.rect(screen, color, pygame.Rect(1440, 660, 1600, 1200))

        # Desired button dimensions
        button_width = 400
        button_height = 200

        # Display Pass button
        pass_button = font.render("YES", True, TEXT_COLOR)
        pass_rect = pygame.Rect(1120 - button_width // 2, 2300 - button_height // 2, button_width, button_height)
        pygame.draw.rect(screen, YELLOW, pass_rect)
        screen.blit(pass_button, pass_button.get_rect(center=pass_rect.center))

        # Display Fail button
        fail_button = font.render("NO", True, TEXT_COLOR)
        fail_rect = pygame.Rect(3360 - button_width // 2, 2300 - button_height // 2, button_width, button_height)
        pygame.draw.rect(screen, BLUE, fail_rect)
        screen.blit(fail_button, fail_button.get_rect(center=fail_rect.center))

        # Display help button
        help_button_rect = pygame.Rect(2100, 2300, 200, 100)
        pygame.draw.rect(screen, GREEN, help_button_rect)
        help_text = font.render("HELP", True, TEXT_COLOR)
        screen.blit(help_text, (help_button_rect.x + 50, help_button_rect.y + 20))

        # Display epoch and success rate
        info_text = font.render(f"Epoch: {epoch}/1000    Success Rate: {pass_count}/{total_count}", True, TEXT_COLOR)
        screen.blit(info_text, (1800, 2400))

        dirty_code_from_tarik = font.render(f"Question: is the color that is visible below green colored?", True, TEXT_COLOR)
        screen.blit(dirty_code_from_tarik, (1550, 420))

        pygame.display.flip()

        wait_for_response = True
        while wait_for_response:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    wait_for_response = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    if pass_rect.collidepoint(x, y):
                        if is_green(color, tolerance):
                            pass_count += 1
                        else:
                            incorrect_sound.play()  # Play sound effect for incorrect response
                        total_count += 1
                        epoch += 1
                        # Gradually decrease tolerance
                        tolerance = max(0, tolerance - 5)
                        wait_for_response = False
                    elif fail_rect.collidepoint(x, y):
                        if not is_green(color, tolerance):
                            pass_count += 1
                        else:
                            incorrect_sound.play()  # Play sound effect for incorrect response
                        total_count += 1
                        epoch += 1
                        wait_for_response = False
                    elif help_button_rect.collidepoint(x, y):
                        help_button_action()
                        wait_for_response = False

        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()
