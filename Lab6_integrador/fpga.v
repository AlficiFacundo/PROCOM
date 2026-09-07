`timescale 1ns / 1ps
//-----------------------------------------------------------------------------
// top level: MicroBlaze + UART + GPIO (uP) <-> Register File (RF) <-> DSP + mem_log
//-----------------------------------------------------------------------------
module fpga (
    out_leds_rgb0,
    out_leds_rgb1,
    out_leds_rgb2,
    out_leds_rgb3,
    out_leds,
    out_tx_uart,
    in_rx_uart,
    in_reset,
    i_sw,
    clk100
);
    parameter NB_GPIOS   = 32;
    parameter NB_LEDS    = 4;
    parameter NB_COEFF   = 9;
    parameter CNT_WIDTH  = 64;
    parameter ADDR_LOG_W = 15;

    output wire [NB_LEDS-1:0] out_leds;
    output [3-1:0]            out_leds_rgb0;
    output [3-1:0]            out_leds_rgb1;
    output [3-1:0]            out_leds_rgb2;
    output [3-1:0]            out_leds_rgb3;

    output wire               out_tx_uart;
    input  wire               in_rx_uart;
    input  wire               in_reset;
    input  wire [3:0]         i_sw;
    input                     clk100;

    wire [NB_GPIOS-1:0] gpo0;
    wire [NB_GPIOS-1:0] gpi0;
    wire                locked;
    wire                clockdsp;

    ///////////////////////////////////////////
    // MicroBlaze
    ///////////////////////////////////////////
    MicroGPIO u_micro (
        .clock100       (clockdsp),
        .gpio_rtl_tri_o (gpo0),
        .gpio_rtl_tri_i (gpi0),
        .reset          (in_reset),
        .sys_clock      (clk100),
        .o_lock_clock   (locked),
        .usb_uart_rxd   (in_rx_uart),
        .usb_uart_txd   (out_tx_uart)
    );

    ///////////////////////////////////////////
    // Register File
    ///////////////////////////////////////////
    wire        rf_rst, rf_enb_tx, rf_enb_rx, rf_run_log, rf_read_log;
    wire        rf_ber_rst;
    wire [1:0]  rf_phase_sel;
    wire [ADDR_LOG_W-1:0] rf_addr_log;
    wire [31:0] rf_data_log_from_mem;
    wire        rf_mem_full;
    wire [CNT_WIDTH-1:0] rf_ber_samp_I, rf_ber_samp_Q, rf_ber_error_I, rf_ber_error_Q;

    register_file #(.CNT_WIDTH(CNT_WIDTH),
                    .ADDR_LOG_W(ADDR_LOG_W),
                    .DATA_W(32)
        ) u_rf (
        .clk(clockdsp), 
        .i_rst_n(locked),
        .i_gpo(gpo0), 
        .o_gpi(gpi0),
        .o_rst(rf_rst), 
        .o_enb_tx(rf_enb_tx), 
        .o_enb_rx(rf_enb_rx),
        .o_phase_sel(rf_phase_sel), 
        .o_run_log(rf_run_log), 
        .o_read_log(rf_read_log),
        .o_addr_log_to_mem(rf_addr_log), 
        .o_ber_rst(rf_ber_rst),
        .i_data_log_from_mem(rf_data_log_from_mem), 
        .i_mem_full(rf_mem_full),
        .i_ber_samp_I(rf_ber_samp_I), 
        .i_ber_samp_Q(rf_ber_samp_Q),
        .i_ber_error_I(rf_ber_error_I), 
        .i_ber_error_Q(rf_ber_error_Q),
        .i_sw(i_sw));

    ///////////////////////////////////////////
    // DSP
    ///////////////////////////////////////////
    wire signed [NB_COEFF-1:0] sample_I, sample_Q;
    wire       ber_ok;
    wire [3:0] dsp_led;

    dsp_core #(.NB_COEFF(NB_COEFF), 
                .CNT_WIDTH(CNT_WIDTH)
        ) u_dsp (
        .clk(clockdsp), 
        .i_rst_n(locked),
        .i_rf_rst(rf_rst), 
        .i_enb_tx(rf_enb_tx), 
        .i_enb_rx(rf_enb_rx),
        .i_phase_sel(rf_phase_sel), 
        .i_rf_ber_rst(rf_ber_rst),
        .o_sample_I(sample_I), 
        .o_sample_Q(sample_Q),
        .o_ber_samp_I(rf_ber_samp_I), 
        .o_ber_samp_Q(rf_ber_samp_Q),
        .o_ber_error_I(rf_ber_error_I), 
        .o_ber_error_Q(rf_ber_error_Q),
        .o_ber_ok(ber_ok), 
        .o_led(dsp_led));

    ///////////////////////////////////////////
    // mem_log
    ///////////////////////////////////////////
    wire [31:0] log_wr_data = { {(16-NB_COEFF){sample_I[NB_COEFF-1]}}, sample_I,
                                 {(16-NB_COEFF){sample_Q[NB_COEFF-1]}}, sample_Q };

    mem_log #(.DATA_W(32), 
                .ADDR_W(ADDR_LOG_W)
        ) u_memlog (
        .clk(clockdsp), 
        .i_rst_n(locked),
        .o_run_log(rf_run_log), 
        .o_read_log(rf_read_log),
        .o_addr_log_to_mem(rf_addr_log), 
        .i_wr_data(log_wr_data),
        .i_data_log_from_mem(rf_data_log_from_mem), 
        .i_mem_full(rf_mem_full));

    ///////////////////////////////////////////
    // Leds
    ///////////////////////////////////////////
    assign out_leds[0] = locked;        // o_lock_clk
    assign out_leds[1] = rf_rst;        // o_rst
    assign out_leds[2] = rf_enb_tx;     // o_enb[0]
    assign out_leds[3] = rf_enb_rx;     // o_enb[1]

    assign out_leds_rgb0 = {rf_mem_full, rf_run_log, rf_read_log}; // estado MEMLog
    assign out_leds_rgb1 = {ber_ok, rf_phase_sel};                 // estado BER/fase
    assign out_leds_rgb2 = 3'b000;
    assign out_leds_rgb3 = 3'b000;

endmodule