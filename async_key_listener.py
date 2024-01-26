from pynput import keyboard
import threading
import _thread

def key_listener():
    # This function will run in a separate thread
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def on_press(key):
    try:
        if key == keyboard.Key.space:
            on_ctrl_c()
    except AttributeError:
        pass

def on_ctrl_c():
    print("Ctrl+C pressed!")
    _thread.interrupt_main()

def listen_for_ctrl_c():
    # Create a thread for the key listener
    listener_thread = threading.Thread(target=key_listener)
    # Set the thread as a daemon, so it will exit when the main program exits
    listener_thread.daemon = True

    # Start the thread
    listener_thread.start()

    # Uncomment the line below if you face issues with exiting the main program
    # listener_thread.join()
