#!/usr/bin/python
import time
from datetime import datetime
import sys
import os
import obd
import pygame
from pygame.locals import *

# Configuration
RESOLUTION = (480,320)
piTFT = True
debug = False
use_console = False
uom = 'imperial'
main_display_value = 'rpm'
rpm_max = 8000
boost_max = 30
connection_timeout = 30

# Variables
run = True
startup = False
paused = False
menu_state = None
connection = None
connecting = True
connection_time = 0
ecu_connected = False
connection_failed = False
engine_running = False

#OBD Variables
elm_voltage = 0
engine_load = 0
rpm = 0
intake_pressure = 0
oil_temp = 0
coolant_temp = 0

# Set up the window. If piTFT flag is set, set up the window for the screen.
# Else create it normally for use on normal monitor.
if piTFT:
    os.putenv('SDL_FBDEV', '/dev/fb1')
    window = pygame.display.set_mode(RESOLUTION, pygame.FULLSCREEN)
else:
    window = pygame.display.set_mode(RESOLUTION, pygame.NOFRAME)

# Initialize
pygame.init()
clock = pygame.time.Clock()
pygame.mouse.set_visible = False

# Console logging
if debug:
    obd.logger.setLevel(obd.logging.DEBUG)

if not use_console:
    now = datetime.now()
    now = now.strftime('%m%d%Y_%H%M%S')
    sys.stdout = open('logs/console_log-' + str(now) + '.txt', 'w')
    print(str(datetime.now()) + ': ' + 'Script started')

# Set up fonts and colors
small_font = pygame.font.Font('font/bmw_helvetica_bold.ttf', 20)
medium_font = pygame.font.Font('font/bmw_helvetica_bold.ttf', 30)
large_font = pygame.font.Font('font/bmw_helvetica_bold.ttf', 40)
xlarge_font = pygame.font.Font('font/bmw_helvetica_bold.ttf', 60)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Create array for gauge images
bg_dir = 'images/gauges/'
bg_files = ['gauge_%i.png' % i for i in range(0, len(os.listdir(bg_dir)))]
bg = [pygame.image.load(os.path.join(bg_dir, file)) for file in bg_files]

# Load images
gauge_bg = pygame.image.load('images/bg/gauge_bg.png').convert_alpha()
logo_img = pygame.image.load('images/m3_logo.png').convert_alpha()
battery_img = pygame.image.load('images/battery.png').convert_alpha()
coolant_img = pygame.image.load('images/coolant_temp.png').convert_alpha()
oil_img = pygame.image.load('images/oil_temp.png').convert_alpha()
back_img = pygame.image.load('images/buttons/button_back.png').convert_alpha()
power_img = pygame.image.load('images/buttons/button_power.png').convert_alpha()
exit_img = pygame.image.load('images/buttons/button_exit.png').convert_alpha()
connect_img = pygame.image.load('images/buttons/button_connect.png').convert_alpha()
connected_img = pygame.image.load('images/buttons/button_connected.png').convert_alpha()

# Create button instances
power_button = pygame.Rect(10, 10, 40, 40)
exit_button = pygame.Rect(430, 10, 40, 40)
connect_button = pygame.Rect(180, 140, 120, 40)

# Functions to draw values
def draw_text(text, x, y, font, color):
    text = font.render(text, True, color)
    text_rect = text.get_rect(center=(x, y))
    window.blit(text, text_rect)

# Gauge function
def get_gauge():
    global gauge_iter
    if main_display_value == 'boost':
        gauge_iter = int(intake_pressure/(boost_max/25))
    elif main_display_value == 'rpm':
        gauge_iter = int(rpm/(rpm_max/25))
        
def connect():
    global connecting, connection, connection_time, connection_timeout, startup, ecu_connected, connection_failed
    print(str(datetime.now()) + ': ' + 'Attempting to connect...')

    # Create the connection
    connection = obd.Async(portstr='/dev/rfcomm0', baudrate=None, protocol=None, fast=True, timeout=connection_timeout, check_voltage=True)

    #Command functions
    def new_elm_voltage(r):
        global elm_voltage
        elm_voltage = r.value.magnitude

    def new_engine_load(r):
        global engine_load
        if not r.is_null():
            engine_load = int(r.value.magnitude)

    def new_rpm(r):
        global rpm
        if not r.is_null():
            rpm = int(r.value.magnitude)

    def new_coolant_temp(r):
        global coolant_temp
        if uom == 'metric':
            coolant_temp = r.value.magnitude
        elif uom == 'imperial':
            coolant_temp = r.value.to('degF')
            coolant_temp = coolant_temp.magnitude

    def new_oil_temp(r):
        global oil_temp
        if uom == 'metric':
            oil_temp = r.value.magnitude
        elif uom == 'imperial':
            oil_temp = r.value.to('degF')
            oil_temp = oil_temp.magnitude

    def new_intake_pressure(r):
        global intake_pressure
        intake_pressure = r.value.to('psi')
        intake_pressure = round(intake_pressure.magnitude, 1)

    if connection_time < connection_timeout:   
        if connection.is_connected():
            # Set up monitors
            connection.watch(obd.commands.ELM_VOLTAGE, callback=new_elm_voltage)
            connection.watch(obd.commands.ENGINE_LOAD, callback=new_engine_load)
            connection.watch(obd.commands.RPM, callback=new_rpm)
            connection.watch(obd.commands.COOLANT_TEMP, callback=new_coolant_temp)
            connection.watch(obd.commands.INTAKE_PRESSURE, callback=new_intake_pressure)
            connection.watch(obd.commands.OIL_TEMP, callback=new_oil_temp)
            connection.start()
            print(str(datetime.now()) + ': ' + 'ECU connected')
            startup = True
            ecu_connected = True
            connection_failed = False
            connecting = False
        else:
            window.fill(0)
            window.blit(logo_img, (169, 120))
            draw_text('Connecting...', 240, 200, small_font, WHITE)
            draw_text('(' + str(connection_time) + ')', 20, 20, small_font, WHITE)
            print(str(datetime.now()) + ': Connection timeout ' + str(connection_timeout - connection_time))
            pygame.display.update()
            connection_time += 1
            pygame.time.wait(1000)
    else:
        connection.stop()
        startup = True
        ecu_connected = False
        connection_failed = True
        connecting = False

def startup_animation():
    global startup

    # Run through gauges then back
    while startup:
        print(str(datetime.now()) + ': ' + 'Starting up')
        for i in range(1, len(bg)):
            window.fill(0)
            window.blit(gauge_bg, (20, 20))
            window.blit(logo_img, (99, 145))
            window.blit(bg[i], (20, 20))
            pygame.display.update()
            clock.tick(60)
        pygame.time.wait(500)

        for i in range(len(bg)-1, -1, -1):
            window.fill(0)
            window.blit(gauge_bg, (20, 20))
            window.blit(logo_img, (99, 145))
            window.blit(bg[i], (20, 20))
            pygame.display.update()
            clock.tick(60)
        pygame.time.wait(500)

        startup = False
        
def car_connected():
    print(str(datetime.now()) + ': Started')
    global ecu_connected, menu_state, paused, engine_running

    while ecu_connected:
        # Event Listeners
        for event in pygame.event.get():
            if event.type == QUIT:
                if ecu_connected:
                    connection.close()
                sys.stdout.close()
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == pygame.K_x:
                    if ecu_connected:
                        connection.close()
                    sys.stdout.close()
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_SPACE:
                    if not paused:
                        paused = True
                        menu_state = 'main'
                    if paused:
                        paused = False
                        menu_state = None
            elif event.type == MOUSEBUTTONDOWN:
                if menu_state == None:
                    paused = True
                    menu_state = 'main'
                elif menu_state == 'main':
                    if exit_button.collidepoint(event.pos):
                        if ecu_connected:
                            connection.close()
                        print(str(datetime.now()) + ': ' + 'User exit')
                        sys.stdout.close()
                        pygame.quit()
                        sys.exit()
                    elif power_button.collidepoint(event.pos):
                        if ecu_connected:
                            connection.close()
                        print(str(datetime.now()) + ': ' + 'Power off')
                        sys.stdout.close()
                        os.system('sudo shutdown -h now')
                        pygame.quit()
                        sys.exit()
                    else:
                        menu_state = None
                        paused = False
                        
        # Draw pause menu
        if paused:
            if menu_state == 'main':
                window.fill(0)
                pygame.draw.rect(window, BLACK, exit_button)
                pygame.draw.rect(window, BLACK, power_button)
                window.blit(exit_img, (430,10))
                window.blit(power_img, (10,10))
                window.blit(connected_img, (180,140))
        else:
            # Draw main display
            window.fill(0)
            get_gauge()
            window.blit(gauge_bg, (20, 20))
            window.blit(logo_img, (99, 145))
            window.blit(bg[gauge_iter], (20, 20))

            if main_display_value == 'rpm':
                draw_text(str(rpm), 180, 260, xlarge_font, WHITE)
                draw_text('RPM', 180, 300, small_font, WHITE)
            elif main_display_value == 'boost':
                draw_text(str(intake_pressure), 180, 260, xlarge_font, WHITE)
                if uom == 'metric':
                    draw_text('bar', 180, 300, small_font, WHITE)
                elif uom == 'imperial':
                    draw_text('psi', 180, 300, small_font, WHITE)

            # Voltage
            window.blit(battery_img, (370-int(battery_img.get_width()/2), 40))
            draw_text(str('{0:.1f}'.format(float(elm_voltage))) + ' V', 440, 55, small_font, WHITE)

            # Temperatures
            window.blit(coolant_img, (370-int(coolant_img.get_width()/2), 140))
            window.blit(oil_img, (370-int(oil_img.get_width()/2), 240))

            if uom == 'metric':
                draw_text(str(round(coolant_temp)) + ' \xb0C', 440, 155, small_font, WHITE)
                draw_text(str(round(oil_temp)) + ' \xb0C', 440, 255, small_font, WHITE)
            elif uom == 'imperial':
                draw_text(str(round(coolant_temp)) + ' \xb0F', 440, 155, small_font, WHITE)
                draw_text(str(round(oil_temp)) + ' \xb0F', 440, 255, small_font, WHITE)

            # Check if car is running
            if not engine_running and engine_load > 0:
                engine_running = True
            elif engine_running and engine_load == 0:
                for i in range(0,9):
                    window.fill(0)
                    window.blit(logo_img, (169, 120))
                    draw_text('Shutting down...', 240, 200, small_font, WHITE)
                    draw_text('(' + str(10-i) + ')', 460, 10, small_font, WHITE)
                    pygame.display.update()
                    pygame.time.wait(1000)
                print(str(datetime.now()) + ': Shutting down...')
                connection.close()
                sys.stdout.close()
                pygame.quit()
                os.system('sudo shutdown -h now')
                sys.exit()

        pygame.display.update()
        clock.tick(60)

def not_connected():
    global connection_failed, connecting, menu_state, paused
    print(str(datetime.now()) + ': Failed to connect')
    
    while connection_failed:
        # Event Listeners
        for event in pygame.event.get():
            if event.type == QUIT:
                sys.stdout.close()
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == pygame.K_x:
                    if ecu_connected:
                        connection.close()
                    sys.stdout.close()
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_SPACE:
                    if not paused:
                        paused = True
                        menu_state = 'main'
                    elif paused:
                        paused = False
                        menu_state = None
            elif event.type == MOUSEBUTTONDOWN:
                if menu_state == None:
                    paused = True
                    menu_state = 'main'
                elif menu_state == 'main':
                    if connect_button.collidepoint(event.pos):
                        print(str(datetime.now()) + ': Retrying connection')
                        menu_state = None
                        paused = False
                        connecting = True
                        connection_failed = False
                    elif exit_button.collidepoint(event.pos):
                        print(str(datetime.now()) + ': User exit')
                        sys.stdout.close()
                        pygame.quit()
                        sys.exit()
                    elif power_button.collidepoint(event.pos):
                        print(str(datetime.now()) + ': Power off')
                        sys.stdout.close()
                        os.system('sudo shutdown -h now')
                        pygame.quit()
                        sys.exit()
                    else:
                        menu_state = None
                        paused = False
        # Draw pause menu
        if paused:
            if menu_state == 'main':
                window.fill(0)
                pygame.draw.rect(window, BLACK, exit_button)
                pygame.draw.rect(window, BLACK, power_button)
                pygame.draw.rect(window, BLACK, connect_button)
                window.blit(power_img, (10,10))
                window.blit(exit_img, (430,10))
                window.blit(connect_img, (180,140))
        else:
            window.fill(0)
            window.blit(gauge_bg, (20, 20))
            window.blit(logo_img, (99, 145))
            window.blit(bg[0], (20, 20))
            window.blit(battery_img, (370-int(battery_img.get_width()/2), 40))
            window.blit(coolant_img, (370-int(coolant_img.get_width()/2), 140))
            window.blit(oil_img, (370-int(oil_img.get_width()/2), 240))
            
        pygame.display.update()
        clock.tick(60)

# Main loop 
while run:
    try:
        if connecting:
            connect()
        elif startup:
            startup_animation()       
        elif ecu_connected:
            car_connected()
        elif connection_failed:
            not_connected()
    except Exception as e:
        print(str(datetime.now()) + ': ' + str(e))
        sys.stdout.close()
        pygame.display.quit()
        sys.exit(1)

sys.stdout.close() 
pygame.display.quit()
sys.exit()
