import pygame
from .config import (
    AXIS_DEADZONE,
    BUTTON_ENTER,
    BUTTON_BACK,
    BUTTON_PAUSE,
)

class InputHandler:
    def __init__(self):
        self.joysticks = []
        self.last_input_action = "None"
        self.last_input_source = "None"
        self.initialize_joysticks()

    def initialize_joysticks(self):
        """Initializes the joystick module and detects connected controllers."""
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()

            self.joysticks = []
            count = pygame.joystick.get_count()
            print(f"Joystick module initialized. Found {count} controllers.")

            for i in range(count):
                try:
                    joystick = pygame.joystick.Joystick(i)
                    joystick.init()
                    self.joysticks.append(joystick)
                    print(f"Initialized controller: {joystick.get_name()}")
                except pygame.error as e:
                    print(f"Error initializing joystick {i}: {e}")

        except pygame.error as e:
            print(f"Warning: Could not initialize joystick module: {e}")

    def process_event(self, ev):
        """
        Processes a single pygame event and returns (action, source).
        Returns (None, None) if no relevant action occurred.
        """
        action = None
        source = None

        if ev.type == pygame.JOYDEVICEADDED or ev.type == pygame.JOYDEVICEREMOVED:
            self.initialize_joysticks()

        # 1. Keyboard Input
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_UP:
                action = "UP"
                source = "KEYBOARD"
            elif ev.key == pygame.K_DOWN:
                action = "DOWN"
                source = "KEYBOARD"
            elif ev.key == pygame.K_LEFT:
                action = "LEFT"
                source = "KEYBOARD"
            elif ev.key == pygame.K_RIGHT:
                action = "RIGHT"
                source = "KEYBOARD"
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                action = "ENTER"
                source = "KEYBOARD"
            elif ev.key == pygame.K_ESCAPE:
                action = "PAUSE"
                source = "KEYBOARD"
            elif ev.key == pygame.K_r:
                action = "RETRY"
                source = "KEYBOARD"
            elif ev.key == pygame.K_m:
                action = "MENU_QUIT"
                source = "KEYBOARD"
            elif ev.key == pygame.K_d:
                action = "TOGGLE_DEBUG"
                source = "KEYBOARD"

        # 2. Controller Input
        elif ev.type == pygame.JOYAXISMOTION:
            if ev.instance_id < len(self.joysticks):
                if ev.axis == 0:  # X-Axis
                    if ev.value < -AXIS_DEADZONE:
                        action = "LEFT"
                        source = "CONTROLLER"
                    elif ev.value > AXIS_DEADZONE:
                        action = "RIGHT"
                        source = "CONTROLLER"
                elif ev.axis == 1:  # Y-Axis
                    if ev.value < -AXIS_DEADZONE:
                        action = "UP"
                        source = "CONTROLLER"
                    elif ev.value > AXIS_DEADZONE:
                        action = "DOWN"
                        source = "CONTROLLER"

        elif ev.type == pygame.JOYHATMOTION:
            if ev.hat == 0:
                x, y = ev.value
                if x == -1:
                    action = "LEFT"
                    source = "CONTROLLER"
                elif x == 1:
                    action = "RIGHT"
                    source = "CONTROLLER"
                elif y == -1:
                    action = "DOWN"
                    source = "CONTROLLER"
                elif y == 1:
                    action = "UP"
                    source = "CONTROLLER"

        elif ev.type == pygame.JOYBUTTONDOWN:
            if ev.button == BUTTON_ENTER:
                action = "ENTER"
                source = "CONTROLLER"
            elif ev.button == BUTTON_BACK:
                action = "PAUSE"
                source = "CONTROLLER"
            elif ev.button == BUTTON_PAUSE:
                action = "PAUSE"
                source = "CONTROLLER"

        if action:
            self.last_input_action = action
            self.last_input_source = source

        return action, source
