def send_pulse_train(sig_gen, current, ton, toff, repeat):
    # Sends a pulse train.

    # Input: - sig_gen = the signal generator serial device (which is outputted when using init_serial_port)
    #        - current = the current in mA
    #        - ton = on time of the pulse in ms
    #        - toff = off time of the pulse in ms
    #        - repeat = number of times the pulse is repeated

    # Output: data (dict) with keys:
    # When no error occurred:
    # - Ver = signal generator version
    # - Serial = serial number of the signal generator
    # - samples = number of samples
    # When the number of samples <= 100:
    # - current = array with measured current in mA (length of array is the number of samples)
    # - voltage = array with measured voltage in volt (length of array is the number of samples)
    # When the number of samples > 100:
    # - MaxCurrent = maximum value of the measured current in mA
    # - MinCurrent = minimum value of the measured current in mA
    # - MaxVolt = maximum value of the measured voltage in volt
    # - MinVolt = minimum value of the measured voltage in volt
    # When one of the values does not meet the requirements or when another error occurs:
    # - Error# = error number
    # - Error = error message

    # NOTE: for more information see the Signal Generator documentation

    # NOTE: when a FakeSerial object with port FAKECOM is passed, a fake data dict with the following values is
    # returned:
    # - Ver = 99
    # - Serial = Fake Signal Generator
    # - samples = repeat
    # - current = 0
    # - voltage = 0

    # NOTE: when communication with the signal generator fails, the output is a string with an error message

    import serial
    import json

    # When the com port address is FAKECOM a fake data dict is created.
    if sig_gen.port == 'FAKECOM':
        data = {
            "Ver": '99',
            "Serial": 'Fake Signal Generator',
            "samples": repeat,
            "current": 0,
            "voltage": 0
        }

        # Wait for the duration of the pulse: (ton + toff) * repeat
        import time
        pulse_duration_sec = ((ton + toff) * repeat) / 1000
        time.sleep(pulse_duration_sec)

        return data

    else:

        try:
            # Write to port (type: bytes)
            pulse_info = "{current:" + str(current) + \
                         ",Ton:" + str(ton) + \
                         ",Toff:" + str(toff) + \
                         ",repeat:" + str(repeat) + \
                         "}\n"

            sig_gen.write(pulse_info.encode())

            # Get data (readline reads a line until line feed '\n', or until the timeout specified when opening the port
            # is reached)
            raw_json_data = sig_gen.readline()
            json_data = raw_json_data.decode('utf-8')
            try:
                data = json.loads(json_data)
            except:
                data = 'Error, no data'

            return data

        # Capture serial communication error
        except serial.serialutil.SerialException:
            return "ERROR: pulse not sent"


# # Test code:
# import init_and_close_serial_device
# sig_gen = init_and_close_serial_device.init_serial_device('COM4')
# data = send_pulse_train(sig_gen, current=0, ton=1, toff=1, repeat=1)
# print(data)
# init_and_close_serial_device.close_serial_device(sig_gen)
