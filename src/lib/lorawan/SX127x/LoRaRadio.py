""" Defines the SX127x (RFM95) class and a few utility functions. """

# modified by Brian N Norman 2023
#
# Copyright 2015 Mayer Analytics Ltd.
#
# This file is part of pySX127x.
#
# pySX127x is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pySX127x is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You can be released from the requirements of the license by obtaining a commercial license. Such a license is
# mandatory as soon as you develop commercial activities involving pySX127x without disclosing the source code of your
# own applications, or shipping pySX127x with a closed source product.
#
# You should have received a copy of the GNU General Public License along with pySX127.  If not, see
# <http://www.gnu.org/licenses/>.


VERBOSE=True # default

# taken from Adafruit_rfm9x library
_RH_RF95_FXOSC = 32000000.0 # The crystal oscillator frequency of the module
_RH_RF95_FSTEP = _RH_RF95_FXOSC / 524288 # The Frequency Synthesizer step = RH_RF95_FXOSC / 2^^19


from LogManager import LogMan
log=LogMan.getLogger("LoraRadio") # use default level

from .constants import *
from .board_config import BOARD
import time

try:
    # these don't appear to exist in the circuitpython installed
    # but were in the adafruit_rfm9x library code
    from typing import Optional, Type, Literal
    from circuitpython_typing import WriteableBuffer, ReadableBuffer
except:
    pass

################################################## Some utility functions ##############################################

def set_bit(value, index, new_bit):
    """ Set the index'th bit of value to new_bit, and return the new value.
    :param value:   The integer to set the new_bit in
    :type value:    int
    :param index: 0-based index
    :param new_bit: New value the bit shall have (0 or 1)
    :return:    Changed value
    :rtype: int
    """
    mask = 1 << index
    value &= ~mask
    if new_bit:
        value |= mask
    return value


def getter(register_address):
    """ The getter decorator reads the register content and calls the decorated function to do
        post-processing.
    :param register_address: Register address
    :return: Register value
    :rtype: int
    """
    def decorator(func):
        def wrapper(self):
            return func(self, self._read_u8(register_address))
        return wrapper
    return decorator


def setter(register_address):
    """ The setter decorator calls the decorated function for pre-processing and
        then writes the result to the register
    :param register_address: Register address
    :return: New register value
    :rtype: int
    """
    def decorator(func):
        def wrapper(self, val):
            self._write_u8(register_address, func(self, val))
            return self._read_u8(register_address)
        return wrapper
    return decorator

############################################### Definition of the LoRa class ###########################################

class LoRa(object):

    mode = None                       # the mode is backed up here
    backup_registers = []
    verbose = True
    dio_mapping = [None] * 6          # store the dio mapping here
    #_BUFFER = bytearray(4)            # for SPI transfers

    def __init__(self, verbose=VERBOSE, do_calibration=True, calibration_freq=868.1):
        """ Init the object
        
        Send the device to sleep, read all registers, and do the calibration (if do_calibration=True)
        :param verbose: Set the verbosity True/False
        :param calibration_freq: call rx_chain_calibration with this parameter. Default is 868
        :param do_calibration: Call rx_chain_calibration, default is True.
        """
        
        self.reset()
        
        try:
            current_mode=self.get_mode() & 0x8F
            current_mode_name=MODE.lookup[current_mode]

            log.info(f"After reset() Mode : {current_mode_name}") # usually 9 = RX+low freq standby
        except:
            # the mode after reet is not listed in constants.py
            # sometimes the modulation type changes after reset
            log.info(f"After reset() Mode : {current_mode} - not listed in constants.py")
        
        
        # backup all all registers
        self.backup_registers = self.get_all_registers()
        
        
        if do_calibration:
            # changing to FSK_STDBY in the calibration routine doesn't seem to work
            # if LongRangeMode has already been selected
            self.set_mode(MODE.FSK_STDBY) # required for rx_calibration, high frequency mode stdby
            self.rx_chain_calibration(calibration_freq)
        
        self.set_mode(MODE.SLEEP)
        # set the dio_ mapping by calling the two get_dio_mapping_* functions
        self.get_dio_mapping_1()
        self.get_dio_mapping_2()
        
        # allow tx/rx to use whole fifo (256 bytes)
        self.set_fifo_tx_base_addr(0)
        self.set_fifo_rx_base_addr(0)

    #########################
    # Taken from https://github.com/adafruit/Adafruit_CircuitPython_RFM9x/blob/main/adafruit_rfm9x.py
    # pylint: disable=no-member
    # Reconsider pylint: disable when this can be tested
    def _read_into(self, address: int, buf: WriteableBuffer, length: Optional[int] = None) -> None:
        # Read a number of bytes from the specified address into the provided
        # buffer.  If length is not specified (the default) the entire buffer
        # will be filled.
        if length is None:
            length = len(buf)
            
        address=address & 0x7F # make sure bit 7 is 0 -> read
        addr=bytearray([address])

        with BOARD.spidev as spidev:
            spidev.write(addr, end=1)
            spidev.readinto(buf, end=length)

    def _read_u8(self, address: int) -> int:
        # Read a single byte from the provided address and return it.
        buf=bytearray(4)
        self._read_into(address, buf, length=1)
        return buf[0]

    def _write_from(self, address: int, buf: ReadableBuffer, length: Optional[int] = None) -> None:
        # Write a number of bytes to the provided address and taken from the
        # provided buffer.  If no length is specified (the default) the entire
        # buffer is written.
        if length is None:
            length = len(buf)
        
        address=(address | 0x80) & 0xFF
        addr = bytearray([address])  # Set top bit to 1 to indicate a write.
        with BOARD.spidev as spidev:
            spidev.write(addr,end=1)
            spidev.write(bytearray(buf), end=length)
                

    def _write_u8(self, address: int, val: int) -> None:
        # Write a byte register to the chip.  Specify the 7-bit address and the
        # 8-bit value to write to that address.

        addr=(address | 0x80) & 0xFF # Set top bit to 1 to indicate a write.
        val=(val & 0xFF)
        
        buf = bytearray([addr,val])
                           
        with BOARD.spidev as spidev:
            spidev.write(buf, end=2)

    def reset(self) -> None:
        """Perform a reset of the chip."""
        # See section 7.2.2 of the datasheet for reset description.
        log.info(f"resetting RFM9x")
        if BOARD.RST is not None:
            BOARD.RST.value = False  # Set Reset Low
            time.sleep(0.0001)  # 100 us
            BOARD.RST.value = True  # set Reset High
            time.sleep(0.005)  # 5 ms

    # All the set/get/read/write functions

    def get_mode(self):
        """ Get the mode
        :return:    current mode reg
        """
        self.mode = self._read_u8(REG.LORA.OP_MODE)
        return self.mode
    
    def get_mode_dict(self):
        """Get the mode
        :return: dict
        """
        mode = self._read_u8(REG.LORA.OP_MODE)
        return dict(
                LongRangeMode     = (mode & 0x80) >> 7,
                AccessSharedReg   = (mode & 0x40) >> 6,
                Reserved          = (mode & 0x30) >> 4,
                LowFrequencyModeOn= (mode & 0x08) >> 3,
                Mode              = (mode & 0x07)
            )
                 

    
    def mode_ready(self,req_mode):
        """check mode ready
        changing from SLEEP to any other mode can take a few ms
        :param req_mode: the target mode
        :return: True if the current mode matches the requested mode else False
        """
        current_mode=self._read_u8(REG.LORA.OP_MODE)
        # debugging print(f"req_mode {hex(req_mode)} current mode {hex(current_mode)}")
        return current_mode==req_mode

    def set_mode(self, mode):
        """ Set the mode
        mode reg bit 7 can only be changed in SLEEP mode. If the bit is about to be changed
        switch to SLEEP first
        :param mode: Set the mode. Use constants.MODE class
        :return:    New mode
        """
        # the mode is backed up in self.mode
        if mode == self.mode:
            return mode
        
        if self.verbose:
            try:
                log.info(f"Set Mode : {MODE.lookup[mode]}")
            except KeyError:
                #
                raise Exception(f"set_mode KeyError mode requested {hex(mode)}")
 
        # check if bit 7 of the mode register is about to change
        current_mode_long_range=self.get_mode() & 0x80
        req_mode_long_range=mode & 0x80
        
        if current_mode_long_range!=req_mode_long_range:
            # mode is requesting a bit 7 change which can only be done from SLEEP mode first
            self._write_u8(REG.LORA.OP_MODE, MODE.SLEEP)
            while not self.mode_ready(MODE.SLEEP):
                time.sleep(0.0001)
 
        # set the mode
        self._write_u8(REG.LORA.OP_MODE, mode)
        while not self.mode_ready(mode):
            time.sleep(0.0001) # mode change can take a short time
        
        self.mode=mode
        return mode

    def write_payload(self, payload):
        """ Get FIFO ready for TX: Set FifoAddrPtr to FifoTxBaseAddr. The transceiver is put into STDBY mode.
        :param payload: Payload to write (list)
        :return:    Written payload
        """
        payload_size = len(payload)
        assert payload_size<252,"payload size cannot exceed 252 bytes"
        
        log.debug(f"write_payload {list(payload)}")
        
        self.set_mode(MODE.STDBY) # if needed
        base_addr = self.get_fifo_tx_base_addr()
        self.set_fifo_addr_ptr(base_addr)

        self.set_payload_length(payload_size)
        self._write_from(REG.LORA.FIFO, payload,payload_size)

        return payload

    def reset_ptr_rx(self):
        """ Get FIFO ready for RX: Set FifoAddrPtr to FifoRxBaseAddr. The transceiver is put into STDBY mode. """
        self.set_mode(MODE.STDBY) # if needed
        base_addr = self.get_fifo_rx_base_addr()
        self.set_fifo_addr_ptr(base_addr)

    def rx_is_good(self):
        """ Check the IRQ flags for RX errors
        :return: True if no errors
        :rtype: bool
        """
        flags = self.get_irq_flags()
        return not any([flags[s] for s in ['valid_header', 'crc_error', 'rx_done', 'rx_timeout']])

    def read_payload(self , nocheck = False):
        """ Read the payload from FIFO
        :param nocheck: If True then check rx_is_good()
        :return: Payload
        :rtype: list[int]
        """
        if not nocheck and not self.rx_is_good():
            return None
        rx_nb_bytes = self.get_rx_nb_bytes()
        fifo_rx_current_addr = self.get_fifo_rx_current_addr()
        self.set_fifo_addr_ptr(fifo_rx_current_addr)

        payload = bytearray([0] * rx_nb_bytes)
        self._read_into(REG.LORA.FIFO,payload)
        return payload

    def get_freq(self): 
        """
        using the same approach as adafruit_rf9x
        
        return current frequency in MHz

        """
        msb = self._read_u8(REG.LORA.FR_MSB)
        mid = self._read_u8(REG.LORA.FR_MID)
        lsb = self._read_u8(REG.LORA.FR_LSB)
        frf = ((msb << 16) | (mid << 8) | lsb) & 0xFFFFFF
        frequency = (frf * _RH_RF95_FSTEP) / 1000000.0
        # often calculated frequency is not quite the same as set
        return round(frequency,2)

    def check_freq(self,MSB,MID,LSB): 
        """
        Sanity check called after setting the registers
        """
        msb = self._read_u8(REG.LORA.FR_MSB)
        mid = self._read_u8(REG.LORA.FR_MID)
        lsb = self._read_u8(REG.LORA.FR_LSB)
        

        if (MSB==msb) and (MID==mid) and (LSB==lsb):
            return
        raise RuntimeError("Frequency check failed")

 
    def set_freq(self, val: Literal[433.0, 915.0]) -> None:
        """
        using same approach as adafruit_rfm9x library
        set the frequency in the range 433-915 Mhz. Your module may not support the full
        range. RFM9x modules have external components which typically optimise for
        434,868 or 915. Driving at a frequency other than spec MAY work but will be sub-optimal
        thus affecting range.
        """
        if val < 240 or val > 960:
            raise RuntimeError("frequency_mhz must be between 240 and 960")
        # Calculate FRF register 24-bit value.
        frf = int((val * 1000000.0) / _RH_RF95_FSTEP) & 0xFFFFFF
        # Extract byte values and update registers.
        msb = frf >> 16
        mid = (frf >> 8) & 0xFF
        lsb = frf & 0xFF
        
        self._write_u8(REG.LORA.FR_MSB, msb)
        self._write_u8(REG.LORA.FR_MID, mid)
        self._write_u8(REG.LORA.FR_LSB, lsb)
        
        # make sure the registers were set correctly
        self.check_freq(msb,mid,lsb)    

    def get_pa_config(self, convert_dBm=False):
        v = self._read_u8(REG.LORA.PA_CONFIG)
        pa_select    = v >> 7
        max_power    = v >> 4 & 0b111
        output_power = v & 0b1111
        if convert_dBm:
            max_power = max_power * .6 + 10.8
            output_power = max_power - (15 - output_power)
        return dict(
                pa_select    = pa_select,
                max_power    = max_power,
                output_power = output_power
            )

    def set_pa_config(self, pa_select=None, max_power=None, output_power=None):
        """ Configure the PA
        :param pa_select: Selects PA output pin, 0->RFO, 1->PA_BOOST
        :param max_power: Select max output power Pmax=10.8+0.6*MaxPower
        :param output_power: Output power Pout=Pmax-(15-OutputPower) if PaSelect = 0,
                Pout=17-(15-OutputPower) if PaSelect = 1 (PA_BOOST pin)
        :return: new register value
        """
        values={'pa_select':pa_select,'max_power':max_power,'output_power':output_power}
        current = self.get_pa_config()
        values = {s: current[s] if values[s] is None else values[s] for s in values}
        
        regbits = (values['pa_select'] << 7) | (values['max_power'] << 4) | (values['output_power'])
        self._write_u8(REG.LORA.PA_CONFIG, regbits)
        return regbits

    @getter(REG.LORA.PA_RAMP)
    def get_pa_ramp(self, val):
        return val & 0b1111

    @setter(REG.LORA.PA_RAMP)
    def set_pa_ramp(self, val):
        return val & 0b1111

    def get_ocp(self, convert_mA=False):
        v = self._read_u8(REG.LORA.OCP)
        ocp_on = v >> 5 & 0x01
        ocp_trim = v & 0b11111
        if convert_mA:
            if ocp_trim <= 15:
                ocp_trim = 45. + 5. * ocp_trim
            elif ocp_trim <= 27:
                ocp_trim = -30. + 10. * ocp_trim
            else:
                assert ocp_trim <= 27
        return dict(
                ocp_on   = ocp_on,
                ocp_trim = ocp_trim
                )

    def set_ocp_trim(self, I_mA):
        assert(I_mA >= 45 and I_mA <= 240)
        ocp_on = self._read_u8(REG.LORA.OCP) >> 5 & 0x01
        if I_mA <= 120:
            v = int(round((I_mA-45.)/5.))
        else:
            v = int(round((I_mA+30.)/10.))
        v = set_bit(v, 5, ocp_on)
        self._write_u8(REG.LORA.OCP, v)
        return v

    def get_lna(self):
        v = self._read_u8(REG.LORA.LNA)
        return dict(
                lna_gain     = v >> 5,
                lna_boost_lf = v >> 3 & 0b11,
                lna_boost_hf = v & 0b11
            )

    def set_lna(self, lna_gain=None, lna_boost_lf=None, lna_boost_hf=None):
        assert lna_boost_hf is None or lna_boost_hf == 0b00 or lna_boost_hf == 0b11
        self.set_mode(MODE.STDBY)
        if lna_gain is not None:
            # Apparently agc_auto_on must be 0 in order to set lna_gain
            self.set_agc_auto_on(lna_gain == GAIN.NOT_USED)

        values={'lna_gain':lna_gain, 'lna_boost_lf':lna_boost_lf,'lna_boost_hf': lna_boost_hf}
        current = self.get_lna()
        values = {s: current[s] if values[s] is None else values[s] for s in values}
        regbits = (values['lna_gain'] << 5) | (values['lna_boost_lf'] << 3) | (values['lna_boost_hf'])
        self._write_u8(REG.LORA.LNA, regbits)
        retval = self._read_u8(REG.LORA.LNA)
        if lna_gain is not None:
            # agc_auto_on must track lna_gain: GAIN=NOT_USED -> agc_auto=ON, otherwise =OFF
            self.set_agc_auto_on(lna_gain == GAIN.NOT_USED)
        return retval

    def set_lna_gain(self, lna_gain):
        self.set_lna(lna_gain=lna_gain)

    def get_fifo_addr_ptr(self):
        return self._read_u8(REG.LORA.FIFO_ADDR_PTR)

    def set_fifo_addr_ptr(self, ptr):
        self._write_u8(REG.LORA.FIFO_ADDR_PTR, ptr)
        return self._read_u8(REG.LORA.FIFO_ADDR_PTR)

    def get_fifo_tx_base_addr(self):
        return self._read_u8(REG.LORA.FIFO_TX_BASE_ADDR)

    def set_fifo_tx_base_addr(self, ptr):
        self._write_u8(REG.LORA.FIFO_TX_BASE_ADDR, ptr)
        return self._read_u8(REG.LORA.FIFO_TX_BASE_ADDR)

    def get_fifo_rx_base_addr(self):
        return self._read_u8(REG.LORA.FIFO_RX_BASE_ADDR)

    def set_fifo_rx_base_addr(self, ptr):
        self._write_u8(REG.LORA.FIFO_RX_BASE_ADDR, ptr)
        return self._read_u8(REG.LORA.FIFO_RX_BASE_ADDR)

    def get_fifo_rx_current_addr(self):
        return self._read_u8(REG.LORA.FIFO_RX_CURR_ADDR)

    def get_fifo_rx_byte_addr(self):
        return self._read_u8(REG.LORA.FIFO_RX_BYTE_ADDR)

    def get_irq_flags_mask(self):
        v = self._read_u8(REG.LORA.IRQ_FLAGS_MASK)
        return dict(
                rx_timeout     = v >> 7 & 0x01,
                rx_done        = v >> 6 & 0x01,
                crc_error      = v >> 5 & 0x01,
                valid_header   = v >> 4 & 0x01,
                tx_done        = v >> 3 & 0x01,
                cad_done       = v >> 2 & 0x01,
                fhss_change_ch = v >> 1 & 0x01,
                cad_detected   = v >> 0 & 0x01,
            )

    def set_irq_flags_mask(self,
                           rx_timeout=None, rx_done=None, crc_error=None, valid_header=None, tx_done=None,
                           cad_done=None, fhss_change_ch=None, cad_detected=None):
        values={'rx_timeout':rx_timeout,
             'rx_done':rx_done,
             'crc_error':crc_error,
             'valid_header':valid_header,
             'tx_done':tx_done,
             'cad_done':cad_done,
             'fhss_change_ch':fhss_change_ch,
             'cad_detected':cad_detected}
        
        v = self._read_u8(REG.LORA.IRQ_FLAGS_MASK)
        for i, s in enumerate(['cad_detected', 'fhss_change_ch', 'cad_done', 'tx_done', 'valid_header',
                               'crc_error', 'rx_done', 'rx_timeout']):
            this_bit = values[s]
            if this_bit is not None:
                v = set_bit(v, i, this_bit)

        self._write_u8(REG.LORA.IRQ_FLAGS_MASK, v)
        return self._read_u8(REG.LORA.IRQ_FLAGS_MASK)

    def get_irq_flags(self):
        v = self._read_u8(REG.LORA.IRQ_FLAGS)
        return dict(
                rx_timeout     = v >> 7 & 0x01,
                rx_done        = v >> 6 & 0x01,
                crc_error      = v >> 5 & 0x01,
                valid_header   = v >> 4 & 0x01,
                tx_done        = v >> 3 & 0x01,
                cad_done       = v >> 2 & 0x01,
                fhss_change_ch = v >> 1 & 0x01,
                cad_detected   = v >> 0 & 0x01,
            )
    

    def set_irq_flags(self,
                      rx_timeout=None, rx_done=None, crc_error=None, valid_header=None, tx_done=None,
                      cad_done=None, fhss_change_ch=None, cad_detected=None):
        values={'rx_timeout':rx_timeout,
             'rx_done':rx_done,
             'crc_error':crc_error,
             'valid_header':valid_header,
             'tx_done':tx_done,
             'cad_done':cad_done,
             'fhss_change_ch':fhss_change_ch,
             'cad_detected':cad_detected}
        
        v = self._read_u8(REG.LORA.IRQ_FLAGS)
        for i, s in enumerate(['cad_detected', 'fhss_change_ch', 'cad_done', 'tx_done', 'valid_header',
                               'crc_error', 'rx_done', 'rx_timeout']):
            this_bit = values[s]
            if this_bit is not None:
                v = set_bit(v, i, this_bit)

        self._write_u8(REG.LORA.IRQ_FLAGS, v)
        return self._read_u8(REG.LORA.IRQ_FLAGS)

    def clear_irq_flags(self,
                        RxTimeout=None, RxDone=None, PayloadCrcError=None, 
                        ValidHeader=None, TxDone=None, CadDone=None, 
                        FhssChangeChannel=None, CadDetected=None):
        
        values={'RxTimeout':RxTimeout,
             'RxDone':RxDone,
             'PayloadCrcError':PayloadCrcError,
             'ValidHeader':ValidHeader,
             'TxDone':TxDone,
             'CadDone':CadDone,
             'FhssChangeChannel':FhssChangeChannel,
             'CadDetected':CadDetected}
        v = 0
        for i, s in enumerate(['CadDetected', 'FhssChangeChannel', 'CadDone', 
                                'TxDone', 'ValidHeader', 'PayloadCrcError', 
                                'RxDone', 'RxTimeout']):
            this_bit = values[s]
            if this_bit is not None:
                v = set_bit(v, eval('MASK.IRQ_FLAGS.' + s), this_bit)
        self._write_u8(REG.LORA.IRQ_FLAGS,v)
        return self._read_u8(REG.LORA.IRQ_FLAGS)

    def get_rx_nb_bytes(self):
        return self._read_u8(REG.LORA.RX_NB_BYTES)

    def get_rx_header_cnt(self):
        buf=bytearray([0]*2)
        self._read_into(REG.LORA.RX_HEADER_CNT_MSB,buf,2)
        return buf[1] + 256 * buf[0]

    def get_rx_packet_cnt(self):
        buf = bytearray([0] * 2)
        self._read_into(REG.LORA.RX_PACKET_CNT_MSB,buf)
        return buf[0] + 256 * buf[1]

    def get_modem_status(self):
        status = self._read_u8(REG.LORA.MODEM_STAT)
        return dict(
                rx_coding_rate    = status >> 5 & 0x03,
                modem_clear       = status >> 4 & 0x01,
                header_info_valid = status >> 3 & 0x01,
                rx_ongoing        = status >> 2 & 0x01,
                signal_sync       = status >> 1 & 0x01,
                signal_detected   = status >> 0 & 0x01
            )

    def get_pkt_snr_value(self):
        v = self._read_u8(REG.LORA.PKT_SNR_VALUE)
        return float(256-v) / 4.

    def get_pkt_rssi_value(self):
        v = self._read_u8(REG.LORA.PKT_RSSI_VALUE)
        return v - 157

    def get_rssi_value(self):
        v = self._read_u8(REG.LORA.RSSI_VALUE)
        return v - 157

    def get_hop_channel(self):
        v = self._read_u8(REG.LORA.HOP_CHANNEL)
        return dict(
                pll_timeout          = v >> 7,
                crc_on_payload       = v >> 6 & 0x01,
                fhss_present_channel = v >> 5 & 0b111111
            )

    def get_modem_config_1(self):
        val = self._read_u8(REG.LORA.MODEM_CONFIG_1)
        return dict(
                bw = val >> 4 & 0x0F,
                coding_rate = val >> 1 & 0x07,
                implicit_header_mode = val & 0x01
            )
        
    def set_modem_config_1(self, bw=None, coding_rate=None, implicit_header_mode=None):
        values = {'bw':bw, 'coding_rate':coding_rate,'implicit_header_mode':implicit_header_mode}
        current = self.get_modem_config_1()
        values = {s: current[s] if values[s] is None else values[s] for s in values}
        regbits = values['implicit_header_mode'] | (values['coding_rate'] << 1) | (values['bw'] << 4)
        self._write_u8(REG.LORA.MODEM_CONFIG_1, regbits)
        return self._read_u8(REG.LORA.MODEM_CONFIG_1)

    def set_bw(self, bw):
        """ Set the bandwidth 0=7.8kHz ... 9=500kHz
        :param bw: A number 0,2,3,...,9
        :return:
        """
        self.set_modem_config_1(bw=bw)

    def set_coding_rate(self, coding_rate):
        """ Set the coding rate 4/5, 4/6, 4/7, 4/8
        :param coding_rate: A number 1,2,3,4
        :return: New register value
        """
        self.set_modem_config_1(coding_rate=coding_rate)

    def set_implicit_header_mode(self, implicit_header_mode):
        self.set_modem_config_1(implicit_header_mode=implicit_header_mode)
        
    def get_modem_config_2(self, include_symb_timout_lsb=False):
        val = self._read_u8(REG.LORA.MODEM_CONFIG_2)
        d = dict(
                spreading_factor = val >> 4 & 0x0F,
                tx_cont_mode = val >> 3 & 0x01,
                rx_crc = val >> 2 & 0x01,
            )
        if include_symb_timout_lsb:
            d['symb_timout_lsb'] = val & 0x03
        return d
        
    def set_modem_config_2(self, spreading_factor=None, tx_cont_mode=None, rx_crc=None):
        values = {'spreading_factor':spreading_factor,'tx_cont_mode':tx_cont_mode,'rx_crc':rx_crc}
        # RegModemConfig2 contains the SymbTimout MSB bits. We tack the back on when writing this register.
        current = self.get_modem_config_2(include_symb_timout_lsb=True)
        values = {s: current[s] if values[s] is None else values[s] for s in values}
        regbits = (values['spreading_factor'] << 4) | (values['tx_cont_mode'] << 3) | (values['rx_crc'] << 2) | current['symb_timout_lsb']
        self._write_u8(REG.LORA.MODEM_CONFIG_2, regbits)
        return self._read_u8(REG.LORA.MODEM_CONFIG_2)

    def set_spreading_factor(self, spreading_factor):
        self.set_modem_config_2(spreading_factor=spreading_factor)

    def set_rx_crc(self, rx_crc):
        self.set_modem_config_2(rx_crc=rx_crc)

    def get_modem_config_3(self):
        val = self._read_u8(REG.LORA.MODEM_CONFIG_3)
        return dict(
                low_data_rate_optim = val >> 3 & 0x01,
                agc_auto_on = val >> 2 & 0x01
            )

    def set_modem_config_3(self, low_data_rate_optim=None, agc_auto_on=None):
        values = {'low_data_rate_optim':low_data_rate_optim,'agc_auto_on':agc_auto_on}
        current = self.get_modem_config_3()
        values = {s: current[s] if values[s] is None else values[s] for s in values}
        regbits = (values['low_data_rate_optim'] << 3) | (values['agc_auto_on'] << 2)
        self._write_u8(REG.LORA.MODEM_CONFIG_3, regbits)
        return self._read_u8(REG.LORA.MODEM_CONFIG_3)

    @setter(REG.LORA.INVERT_IQ)
    def set_invert_iq(self, invert):
        """ Invert the LoRa I and Q signals
        :param invert: 0: normal mode, 1: I and Q inverted
        :return: New value of register
        """
        return 0x27 | (invert & 0x01) << 6
        
    @getter(REG.LORA.INVERT_IQ)
    def get_invert_iq(self, val):
        """ Get the invert the I and Q setting
        :return: 0: normal mode, 1: I and Q inverted
        """
        return (val >> 6) & 0x01

    def get_agc_auto_on(self):
        return self.get_modem_config_3()['agc_auto_on']

    def set_agc_auto_on(self, agc_auto_on):
        self.set_modem_config_3(agc_auto_on=agc_auto_on)

    def get_low_data_rate_optim(self):
        return self.set_modem_config_3()['low_data_rate_optim']

    def set_low_data_rate_optim(self, low_data_rate_optim):
        self.set_modem_config_3(low_data_rate_optim=low_data_rate_optim)

    def get_symb_timeout(self):

        msb=self._read_u8(REG.LORA.MODEM_CONFIG_2)    # the MSB bits are stored in REG.LORA.MODEM_CONFIG_2
        msb=msb & 0b11

        lsb=self._read_u8(REG.LORA.SYMB_TIMEOUT_LSB)
        return lsb+msb*256

    def set_symb_timeout(self, timeout):
        bkup_reg_modem_config_2 = self._read_u8(REG.LORA.MODEM_CONFIG_2)
        msb = timeout >> 8 & 0b11    # bits 8-9
        lsb = timeout - 256 * msb    # bits 0-7
        reg_modem_config_2 = bkup_reg_modem_config_2 & 0xFC | msb    # bits 2-7 of bkup_reg_modem_config_2 ORed with the two msb bits

        old_msb=self._read_u8(REG.LORA.MODEM_CONFIG_2) & 0x03
        self._write_u8(REG.LORA.MODEM_CONFIG_2,reg_modem_config_2)

        old_lsb = self._read_u8(REG.LORA.SYMB_TIMEOUT_LSB)
        self._write_u8(REG.LORA.SYMB_TIMEOUT_LSB, lsb)
        return old_lsb + 256 * old_msb

    def get_preamble(self):
        buf=bytearray(2) # msb,lsb
        self._read_into(REG.LORA.PREAMBLE_MSB,buf,2)
        return int.from_bytes(buf,'big')

    def set_preamble(self, preamble):
        buf = bytearray(2)  # old_msb,old_lsb
        self._read_into(REG.LORA.PREAMBLE_MSB, buf, 2)

        old_preamble=int.from_bytes(buf,byteorder='big')

        buf=preamble.to_bytes(2,'big')

        self._write_from(REG.LORA.PREAMBLE_MSB,buf,2)

        return old_preamble
        
    @getter(REG.LORA.PAYLOAD_LENGTH)
    def get_payload_length(self, val):
        return val

    @setter(REG.LORA.PAYLOAD_LENGTH)
    def set_payload_length(self, payload_length):
        return payload_length

    @getter(REG.LORA.MAX_PAYLOAD_LENGTH)
    def get_max_payload_length(self, val):
        return val

    @setter(REG.LORA.MAX_PAYLOAD_LENGTH)
    def set_max_payload_length(self, max_payload_length):
        return max_payload_length

    @getter(REG.LORA.HOP_PERIOD)
    def get_hop_period(self, val):
        return val

    @setter(REG.LORA.HOP_PERIOD)
    def set_hop_period(self, hop_period):
        return hop_period

    def get_fei(self):
        buff=bytearray(4)
        self._read_into(REG.LORA.FEI_MSB, buff)
        
        msb=buff[0]
        mid=buff[1]
        lsb=buff[2]
        
        msb &= 0x0F
        freq_error = lsb + 256 * (mid + 256 * msb)
        return freq_error

    @getter(REG.LORA.DETECT_OPTIMIZE)
    def get_detect_optimize(self, val):
        """ Get LoRa detection optimize setting
        :return: detection optimize setting 0x03: SF7-12, 0x05: SF6

        """
        return val & 0b111

    @setter(REG.LORA.DETECT_OPTIMIZE)
    def set_detect_optimize(self, detect_optimize):
        """ Set LoRa detection optimize
        :param detect_optimize 0x03: SF7-12, 0x05: SF6
        :return: New register value
        """
        assert detect_optimize == 0x03 or detect_optimize == 0x05
        return detect_optimize & 0b111

    @getter(REG.LORA.DETECTION_THRESH)
    def get_detection_threshold(self, val):
        """ Get LoRa detection threshold setting
        :return: detection threshold 0x0A: SF7-12, 0x0C: SF6

        """
        return val

    @setter(REG.LORA.DETECTION_THRESH)
    def set_detection_threshold(self, detect_threshold):
        """ Set LoRa detection optimize
        :param detect_threshold 0x0A: SF7-12, 0x0C: SF6
        :return: New register value
        """
        assert detect_threshold == 0x0A or detect_threshold == 0x0C
        return detect_threshold

    @getter(REG.LORA.SYNC_WORD)
    def get_sync_word(self, sync_word):
        return sync_word

    @setter(REG.LORA.SYNC_WORD)
    def set_sync_word(self, sync_word):
        return sync_word

    @getter(REG.LORA.DIO_MAPPING_1)
    def get_dio_mapping_1(self, mapping):
        """ Get mapping of pins DIO0 to DIO3. Object variable dio_mapping will be set.
        :param mapping: Register value
        :type mapping: int
        :return: Value of the mapping list
        :rtype: list[int]
        """
        self.dio_mapping = [mapping>>6 & 0x03, mapping>>4 & 0x03, mapping>>2 & 0x03, mapping>>0 & 0x03] \
                           + self.dio_mapping[4:6]
        return mapping

    @setter(REG.LORA.DIO_MAPPING_1)
    def set_dio_mapping_1(self, mapping):
        """ Set mapping of pins DIO0 to DIO3. Object variable dio_mapping will be set.
        :param mapping: Register value
        :type mapping: int
        :return: New value of the register
        :rtype: int
        """
        self.dio_mapping = [mapping>>6 & 0x03, mapping>>4 & 0x03, mapping>>2 & 0x03, mapping>>0 & 0x03] \
                           + self.dio_mapping[4:6]
        return mapping

    @getter(REG.LORA.DIO_MAPPING_2)
    def get_dio_mapping_2(self, mapping):
        """ Get mapping of pins DIO4 to DIO5. Object variable dio_mapping will be set.
        :param mapping: Register value
        :type mapping: int
        :return: Value of the mapping list
        :rtype: list[int]
        """
        self.dio_mapping = self.dio_mapping[0:4] + [mapping>>6 & 0x03, mapping>>4 & 0x03]
        return self.dio_mapping

    @setter(REG.LORA.DIO_MAPPING_2)
    def set_dio_mapping_2(self, mapping):
        """ Set mapping of pins DIO4 to DIO5. Object variable dio_mapping will be set.
        :param mapping: Register value
        :type mapping: int
        :return: New value of the register
        :rtype: int
        """
        assert mapping & 0b00001110 == 0
        self.dio_mapping = self.dio_mapping[0:4] + [mapping>>6 & 0x03, mapping>>4 & 0x03]
        return mapping

    def get_dio_mapping(self):
        """ Utility function that returns the list of current DIO mappings. Object variable dio_mapping will be set.
        :return: List of current DIO mappings
        :rtype: list[int]
        """
        self.get_dio_mapping_1()
        return self.get_dio_mapping_2()

    def set_dio_mapping(self, mapping):
        """ Utility function that returns the list of current DIO mappings. Object variable dio_mapping will be set.
        :param mapping: DIO mapping list
        :type mapping: list[int]
        :return: New DIO mapping list
        :rtype: list[int]
        """
        mapping_1 = (mapping[0] & 0x03) << 6 | (mapping[1] & 0x03) << 4 | (mapping[2] & 0x3) << 2 | mapping[3] & 0x3
        mapping_2 = (mapping[4] & 0x03) << 6 | (mapping[5] & 0x03) << 4
        self.set_dio_mapping_1(mapping_1)
        return self.set_dio_mapping_2(mapping_2)

    @getter(REG.LORA.VERSION)
    def get_version(self, version):
        """ Version code of the chip.
            Bits 7-4 give the full revision number; bits 3-0 give the metal mask revision number.
        :return: Version code
        :rtype: int
        """
        return version

    @getter(REG.LORA.TCXO)
    def get_tcxo(self, tcxo):
        """ Get TCXO or XTAL input setting
            0 -> "XTAL": Crystal Oscillator with external Crystal
            1 -> "TCXO": External clipped sine TCXO AC-connected to XTA pin
        :param tcxo: 1=TCXO or 0=XTAL input setting
        :return: TCXO or XTAL input setting
        :type: int (0 or 1)
        """
        return tcxo & 0b00010000

    @setter(REG.LORA.TCXO)
    def set_tcxo(self, tcxo):
        """ Make TCXO or XTAL input setting.
            0 -> "XTAL": Crystal Oscillator with external Crystal
            1 -> "TCXO": External clipped sine TCXO AC-connected to XTA pin
        :param tcxo: 1=TCXO or 0=XTAL input setting
        :return: new TCXO or XTAL input setting
        """
        return (tcxo >= 1) << 4 | 0x09      # bits 0-3 must be 0b1001

    @getter(REG.LORA.PA_DAC)
    def get_pa_dac(self, pa_dac):
        """ Enables the +20dBm option on PA_BOOST pin
            False -> Default value
            True  -> +20dBm on PA_BOOST when OutputPower=1111
        :return: True/False if +20dBm option on PA_BOOST on/off
        :rtype: bool
        """
        pa_dac &= 0x07      # only bits 0-2
        if pa_dac == 0x04:
            return False
        elif pa_dac == 0x07:
            return True
        else:
            raise RuntimeError("Bad PA_DAC value %s" % hex(pa_dac))

    @setter(REG.LORA.PA_DAC)
    def set_pa_dac(self, pa_dac):
        """ Enables the +20dBm option on PA_BOOST pin
            False -> Default value
            True  -> +20dBm on PA_BOOST when OutputPower=1111
        :param pa_dac: 1/0 if +20dBm option on PA_BOOST on/off
        :return: New pa_dac register value
        :rtype: int
        """
        return 0x87 if pa_dac else 0x84

    def rx_chain_calibration(self, freq=868.):
        """ Run the image calibration (see Semtech documentation section 4.2.3.8)
        :param freq: Frequency for the HF calibration
        :return: None
        """
        # backup some registers
        op_mode_bkup = self.get_mode()
        pa_config_bkup = self.get_register(REG.LORA.PA_CONFIG)
        freq_bkup = self.get_freq()
        # for image calibration device must be in FSK standby mode
        self.set_mode(MODE.FSK_STDBY)
        # cut the PA
        self.set_register(REG.LORA.PA_CONFIG, 0x00)
        # calibration for the LF band
        image_cal = (self.get_register(REG.FSK.IMAGE_CAL) & 0xBF) | 0x40
        self.set_register(REG.FSK.IMAGE_CAL, image_cal)
        while (self.get_register(REG.FSK.IMAGE_CAL) & 0x20) == 0x20:
            pass
        # Set a Frequency in HF band
        self.set_freq(freq)
        # calibration for the HF band
        image_cal = (self.get_register(REG.FSK.IMAGE_CAL) & 0xBF) | 0x40
        self.set_register(REG.FSK.IMAGE_CAL, image_cal)
        while (self.get_register(REG.FSK.IMAGE_CAL) & 0x20) == 0x20:
            pass
        # put back the saved parameters
        self.set_mode(op_mode_bkup)
        self.set_register(REG.LORA.PA_CONFIG, pa_config_bkup)
        self.set_freq(freq_bkup)

    def dump_registers(self):
        """ Returns a list of [reg_addr, reg_name, reg_value] tuples. Chip is put into mode SLEEP.
        :return: List of [reg_addr, reg_name, reg_value] tuples
        :rtype: list[tuple]
        """
        self.set_mode(MODE.SLEEP)
        values = self.get_all_registers()
        print("dump_registers values",values)
        skip_set = [REG.LORA.FIFO]
        result_list = []
        result_list=[]

        for i, s in iter(REG.LORA.lookup):
            if i in skip_set:
                continue
            v = values[i]
            result_list.append((i, s, v))
        return result_list

    def get_register(self, register_address):
        return self._read_u8(register_address)

    def set_register(self, register_address, val):
        return self._write_u8(register_address, val)

    def get_all_registers(self):
        # read all registers
        # Not sure this is ever used __str__ would be better for debugging

        reg=bytearray([0]*0x3E)

        self._read_into(1,reg) # reg 0 is a fifo so we skip that
        self.mode = self.get_mode() # why?

        return bytearray([0])+reg

    def __del__(self):
        self.set_mode(MODE.SLEEP)

    def debug_dump_registers(self):
        addr=1
        while addr<0x26:
            val=self._read_u8(addr)
            print(f"addr {hex(addr)} val  {val} {hex(val)} {bin(val)}")
            addr+=1
            

    def __str__(self):
        # don't use __str__ while in any mode other than SLEEP or STDBY
        assert(self.mode == MODE.SLEEP or self.mode == MODE.STDBY)

        onoff = lambda i: 'ON' if i else 'OFF'
        f = self.get_freq()
        cfg1 = self.get_modem_config_1()
        cfg2 = self.get_modem_config_2()
        cfg3 = self.get_modem_config_3()
        pa_config = self.get_pa_config(convert_dBm=True)
        ocp = self.get_ocp(convert_mA=True)
        lna = self.get_lna()
        s =  "SX127x LoRa registers:\n"
        s += " mode               %s\n" % MODE.lookup[self.get_mode()]
        s += " freq               %f MHz\n" % f
        s += " coding_rate        %s\n" % CODING_RATE.lookup[cfg1['coding_rate']]
        s += " bw                 %s\n" % BW.lookup[cfg1['bw']]
        s += " spreading_factor   %s chips/symb\n" % (1 << cfg2['spreading_factor'])
        s += " implicit_hdr_mode  %s\n" % onoff(cfg1['implicit_header_mode'])
        s += " rx_payload_crc     %s\n" % onoff(cfg2['rx_crc'])
        s += " tx_cont_mode       %s\n" % onoff(cfg2['tx_cont_mode'])
        s += " preamble           %d\n" % self.get_preamble()
        s += " low_data_rate_opti %s\n" % onoff(cfg3['low_data_rate_optim'])
        s += " agc_auto_on        %s\n" % onoff(cfg3['agc_auto_on'])
        s += " symb_timeout       %s\n" % self.get_symb_timeout()
        s += " freq_hop_period    %s\n" % self.get_hop_period()
        s += " hop_channel        %s\n" % self.get_hop_channel()
        s += " payload_length     %s\n" % self.get_payload_length()
        s += " max_payload_length %s\n" % self.get_max_payload_length()
        s += " irq_flags_mask     %s\n" % self.get_irq_flags_mask()
        s += " irq_flags          %s\n" % self.get_irq_flags()
        s += " rx_nb_byte         %d\n" % self.get_rx_nb_bytes()
        s += " rx_header_cnt      %d\n" % self.get_rx_header_cnt()
        s += " rx_packet_cnt      %d\n" % self.get_rx_packet_cnt()
        s += " pkt_snr_value      %f\n" % self.get_pkt_snr_value()
        s += " pkt_rssi_value     %d\n" % self.get_pkt_rssi_value()
        s += " rssi_value         %d\n" % self.get_rssi_value()
        s += " fei                %d\n" % self.get_fei()
        s += " pa_select          %s\n" % PA_SELECT.lookup[pa_config['pa_select']]
        s += " max_power          %f dBm\n" % pa_config['max_power']
        s += " output_power       %f dBm\n" % pa_config['output_power']
        s += " ocp                %s\n"     % onoff(ocp['ocp_on'])
        s += " ocp_trim           %f mA\n"  % ocp['ocp_trim']
        s += " lna_gain           %s\n" % GAIN.lookup[lna['lna_gain']]
        s += " lna_boost_lf       %s\n" % bin(lna['lna_boost_lf'])
        s += " lna_boost_hf       %s\n" % bin(lna['lna_boost_hf'])
        s += " detect_optimize    %#02x\n" % self.get_detect_optimize()
        s += " detection_thresh   %#02x\n" % self.get_detection_threshold()
        s += " sync_word          %#02x\n" % self.get_sync_word()
        s += " dio_mapping 0..5   %s\n" % self.get_dio_mapping()
        s += " tcxo               %s\n" % ['XTAL', 'TCXO'][self.get_tcxo()]
        s += " pa_dac             %s\n" % ['default', 'PA_BOOST'][self.get_pa_dac()]
        s += " fifo_addr_ptr      %#02x\n" % self.get_fifo_addr_ptr()
        s += " fifo_tx_base_addr  %#02x\n" % self.get_fifo_tx_base_addr()
        s += " fifo_rx_base_addr  %#02x\n" % self.get_fifo_rx_base_addr()
        s += " fifo_rx_curr_addr  %#02x\n" % self.get_fifo_rx_current_addr()
        s += " fifo_rx_byte_addr  %#02x\n" % self.get_fifo_rx_byte_addr()
        s += " status             %s\n" % self.get_modem_status()
        s += " version            %#02x\n" % self.get_version()
        return s
