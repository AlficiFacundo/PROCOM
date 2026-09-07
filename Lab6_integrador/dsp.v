`timescale 1ns / 1ps
//-----------------------------------------------------------------------------
// dsp.v
// Bloque DSP: PRBS9 -> RC Tx I/Q -> Decimador -> Ber I/Q,
// mas la logica de control (deteccion de cambio de fase -> reset_ber).
//-----------------------------------------------------------------------------
module dsp_core #(
    parameter NB_COEFF   = 9,
    parameter NBF_COEFF  = 7,
    parameter N_BAUDS    = 6,
    parameter N_PHASES   = 4,
    parameter CNT_WIDTH  = 64,
    parameter [8:0] SEED_I = 9'h1AA,
    parameter [8:0] SEED_Q = 9'h1FE
)(
    input  wire                        clk,
    input  wire                        i_rst_n,     // reset duro de la FPGA

    // Desde el RF
    input  wire                        i_rf_rst,    // reset via uP
    input  wire                        i_enb_tx,
    input  wire                        i_enb_rx,
    input  wire [1:0]                  i_phase_sel,
    input  wire                        i_rf_ber_rst,   // reset manual de BER

    // Hacia el RF / MEMLog
    output wire signed [NB_COEFF-1:0]  o_sample_I,
    output wire signed [NB_COEFF-1:0]  o_sample_Q,
    output wire [CNT_WIDTH-1:0]        o_ber_samp_I,
    output wire [CNT_WIDTH-1:0]        o_ber_samp_Q,
    output wire [CNT_WIDTH-1:0]        o_ber_error_I,
    output wire [CNT_WIDTH-1:0]        o_ber_error_Q,
    output wire                        o_ber_ok,

    output wire [3:0]                  o_led
);
    wire i_reset = i_rst_n & ~i_rf_rst;

    wire en_tx, en_rx, reset_ber;
    wire [$clog2(N_PHASES)-1:0] phase_sw = i_phase_sel;

    control #(.N_PHASES(N_PHASES)
        ) u_control (
        .clk(clk),
        .i_rst_n(i_reset),
        .i_sw({i_phase_sel, i_enb_rx, i_enb_tx}),
        .en_tx(en_tx),
        .en_rx(en_rx),
        .phase_sw(),
        .reset_ber(reset_ber));

    // reset_ber automatico (cambio de fase) OR reset manual desde el RF
    wire reset_ber_comb = reset_ber | i_rf_ber_rst;

    wire [$clog2(N_PHASES)-1:0] phase_cnt;
    wire valid;

    freq_divider #(.N_PHASES(N_PHASES)
        ) u_div (
        .clk(clk),
        .i_rst_n(i_reset),
        .en_tx(en_tx),
        .phase_cnt(phase_cnt),
        .valid(valid));

    wire prbs_bit_I, prbs_bit_Q;

    prbs9 #(.SEED(SEED_I)
        ) u_prbs_I (
        .prbs_bit(prbs_bit_I),
        .clk(clk),
        .i_rst_n(i_reset),
        .en_tx(en_tx),
        .prbs_en(valid));

    prbs9 #(.SEED(SEED_Q)
        ) u_prbs_Q (
        .prbs_bit(prbs_bit_Q),
        .clk(clk),
        .i_rst_n(i_reset),
        .en_tx(en_tx),
        .prbs_en(valid));

    rc_tx #(.NB_COEFF(NB_COEFF),
            .NBF_COEFF(NBF_COEFF),
            .N_BAUDS(N_BAUDS), 
            .N_PHASES(N_PHASES)
        ) u_rc_I (
            .clk(clk), 
            .i_rst_n(i_reset), 
            .en_tx(en_tx),
            .prbs_bit(prbs_bit_I), 
            .prbs_en(valid),
            .phase_sel(phase_cnt), 
            .data_out(o_sample_I));

    rc_tx #(.NB_COEFF(NB_COEFF), 
            .NBF_COEFF(NBF_COEFF),
            .N_BAUDS(N_BAUDS), 
            .N_PHASES(N_PHASES)
        ) u_rc_Q (
            .clk(clk), 
            .i_rst_n(i_reset), 
            .en_tx(en_tx),
            .prbs_bit(prbs_bit_Q), 
            .prbs_en(valid),
            .phase_sel(phase_cnt), 
            .data_out(o_sample_Q));

    wire valid_dec, dec_bit_I, dec_bit_Q;
    wire signed [NB_COEFF-1:0] dec_sample_I, dec_sample_Q;

    decimator #(.NB_COEFF(NB_COEFF), 
                .N_PHASES(N_PHASES)
        ) u_dec (
            .clk(clk), 
            .i_rst_n(i_reset), 
            .en_rx(en_rx), 
            .en_tx(en_tx),
            .phase_cnt(phase_cnt), 
            .phase_sw(phase_sw),
            .data_in_I(o_sample_I), 
            .data_in_Q(o_sample_Q),
            .valid_dec(valid_dec),
            .dec_bit_I(dec_bit_I), 
            .dec_bit_Q(dec_bit_Q),
            .dec_sample_I(dec_sample_I), 
            .dec_sample_Q(dec_sample_Q));

    ber_counter #(.SEED(SEED_I), 
                .CNT_WIDTH(CNT_WIDTH), 
                .N_PHASES(N_PHASES)
        ) u_ber_I (
            .clk(clk), 
            .i_rst_n(i_reset), 
            .reset_ber(reset_ber_comb),
            .phase_sw(phase_sw), 
            .valid_dec(valid_dec), 
            .dec_bit(dec_bit_I),
            .o_err(o_ber_error_I), 
            .o_tot(o_ber_samp_I));

    ber_counter #(.SEED(SEED_Q), 
                .CNT_WIDTH(CNT_WIDTH), 
                .N_PHASES(N_PHASES)
        ) u_ber_Q (
            .clk(clk), 
            .i_rst_n(i_reset), 
            .reset_ber(reset_ber_comb),
            .phase_sw(phase_sw), 
            .valid_dec(valid_dec),
            .dec_bit(dec_bit_Q),
            .o_err(o_ber_error_Q), 
            .o_tot(o_ber_samp_Q));

    assign o_ber_ok = (o_ber_samp_I > 0) && (o_ber_error_I == 0) &&
                       (o_ber_samp_Q > 0) && (o_ber_error_Q == 0);
    assign o_led = {en_rx, en_tx, phase_sw};

endmodule