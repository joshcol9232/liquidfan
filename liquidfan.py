#!/bin/python

from liquidctl import find_liquidctl_devices
import time

# List of points on fan curve
# (temperature, fan percentage)
# Maximum allowable temperature imo is 60 degrees for the liquid temperature.
FAN_CONFIGS = [
    [(20, 40), (30, 40), (30, 60), (60, 100)],        # CPU Radiator fan
    [(20, 0), (27, 0), (27, 30), (30, 30), (30, 40), (60, 100)] # Top fans
]

PWM_FILE_LOCS = [r"/sys/class/hwmon/hwmon4/pwm2", r"/sys/class/hwmon/hwmon4/pwm3"]



# Returns the speed as a value between 0 and 1
def get_speed_from_curve(T, fan_config):
    # Linear interpolation between points
    # First of all find the bracket that we fall into
    lower_temp = 0
    lower_speed = 0

    upper_temp = None
    upper_speed = None

    for temp, speed in fan_config:
        upper_temp = temp
        upper_speed = speed
        if temp > T:
            break
        lower_temp = temp
        lower_speed = speed

    if upper_temp <= lower_temp:    # If at maximum temperature, return the last speed
        return upper_speed

    # Get equation for line
    # dy/dx
    m = (upper_speed - lower_speed)/(upper_temp - lower_temp)
    # c = y - mx
    c = upper_speed - m * upper_temp

    # y = mx + c
    speed = m * T + c

    return speed/100
    

# Updates the pwm file with the value
def set_fan_speed_from_temp(T, last, fan_config, pwm_file_loc):
    speed = int(get_speed_from_curve(T, fan_config) * 255)

    if speed != last:   # If speed has changed
        # Note that fan speed is set from 0 to 255 in the sys file
        with open(pwm_file_loc, "w") as pwm_file:
            write_string = "%d" % speed
            print(write_string)
            pwm_file.write(write_string)

    return speed


if __name__ == "__main__":
    nzxt_device = None

    for dev in find_liquidctl_devices():
        if nzxt_device:
            break

        # connect to the device (here a context manager is used, but the
        # connection can also be manually managed)
        with dev.connect():
            if "NZXT Kraken" in dev.description:
                print("FOUND KRAKEN")
                nzxt_device = dev


    with nzxt_device.connect() as con:
        init_status = con.initialize()
        print(init_status)

        last_values = [None for _i in range(len(FAN_CONFIGS))]
        while True:
            status = con.get_status()
            print(status)

            # get liquid temperature in degrees C
            liq_temp = status[0][1]

            # update fans
            for i in range(len(FAN_CONFIGS)):
                last_values[i] = set_fan_speed_from_temp(liq_temp, last_values[i], FAN_CONFIGS[i], PWM_FILE_LOCS[i])
                print("Speed for fan %d: %d" % (i, last_values[i]))

            time.sleep(1)
        