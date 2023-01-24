def init_serial_port(com_port):
    # Initializes the serial port: configure port and open port.

    # Input: com port address (e.g. COM4)
    # Output: a serial device

    # NOTE: when the com_port is FAKECOM, a FakeSerial object is created and returned.

    # NOTE: when communication with the signal generator fails, the output is a string with an error message

    import serial

    # When the com port address is FAKECOM a FakeSerial object is created.
    if com_port == 'FAKECOM':

        class FakeSerial:
            def __init__(self):
                self.port = com_port

        ser = FakeSerial()

    else:

        # Create serial device
        ser = serial.Serial()

        try:
            # Configure port
            ser.port = com_port
            ser.baudrate = 115200
            ser.bytesize = 8
            ser.parity = 'N'
            ser.stopbits = 1

            ser.timeout = 10

            # Open serial device
            ser.open()

        # Capture serial communication error
        except serial.serialutil.SerialException:
            ser.close()
            ser = 'ERROR: could not open serial device'

    return ser


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
            data = json.loads(json_data)

            return data

        # Capture serial communication error
        except serial.serialutil.SerialException:
            return "ERROR: pulse not sent"


def close_serial_device(sig_gen):
    # Closes the signal generator
    # Input: the signal generator serial device

    if sig_gen.port != 'FAKECOM':
        sig_gen.close()


def get_com_port():
    # Gets the com port address. First, the com port(s) with description Arduino Leonardo or USB Serial Device is found.
    # Then, a pulse with current = 0 is sent to the device(s). When the Serial key is found in the outputted data, the
    # device is assumed to be a signal generator. When only one signal generator is found, the com port address is
    # returned. When 0 or more than 1 signal generators are found, FAKECOM is returned as com port address.

    # Output: the com port address to which a signal generator is connected.

    # Get serial port addresses
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()

    # init
    com_port = 'FAKECOM'
    port_names = []

    # Loop through ports and find ports with name Arduino Leonardo or USB Serial Device
    for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))
        if desc.find("Arduino Leonardo") != -1 or \
                desc.find("USB Serial Device") != -1:
            port_names.append(port)

    # when devices are found, get their actual name
    if len(port_names) != 0:

        # init
        sig_gen = []
        sig_gen_port = []

        # loop through ports
        for port in port_names:

            # open port
            ser_device = init_serial_port(port)

            # When the ser_device is a string, it contains an error message
            if type(ser_device) == str:
                print('ERROR, could not open COM port. Using FAKECOM.')
            else:
                # send pulse and get name
                data = send_pulse_train(ser_device, current=0, ton=1, toff=1, repeat=1)
                if 'Serial' in data:
                    sig_gen.append(data['Serial'])
                    sig_gen_port.append(port)

                # close port
                close_serial_device(ser_device)

        if len(sig_gen) == 1:  # When only one signal generator is found:
            com_port = sig_gen_port[0]
            print('One signal generator found. Using device {} on port {}'.format(sig_gen[0], com_port))
        else:  # When more than 1 or no signal generators are found:
            print('More than 1 or no signal generators found. Using FAKECOM.')

    else:  # When no serial devices with name Arduino Leonardo or USB Serial Device are found:
        print('No devices found. Using FAKECOM.')

    return com_port


# # Test functions:
# COM_port = get_com_port()
# signal_generator = init_serial_port(COM_port)
# cur_data = send_pulse_train(signal_generator, current=3.3, ton=10, toff=10, repeat=200)
# close_serial_device(signal_generator)
