module top_level #(
    parameter NB_COEFF   = 9,
    parameter NBF_COEFF  = 7,
    parameter N_BAUDS    = 6,
    parameter N_PHASES   = 4,
    parameter CNT_WIDTH  = 24,
    parameter [8:0] SEED_I = 9'h1AA,
    parameter [8:0] SEED_Q = 9'h1FE
)(
    input  wire                 clock,
    output wire [3:0]           o_led
);
    wire en_tx, en_rx, reset_ber;
    wire [$clog2(N_PHASES)-1:0] phase_sw;
    wire [3:0]                  i_sw;
    wire                        i_reset;
    wire                        o_ber_ok;
    wire signed [NB_COEFF-1:0]  o_sample_I;
    wire signed [NB_COEFF-1:0]  o_sample_Q;
    wire [CNT_WIDTH-1:0]        o_err_I;
    wire [CNT_WIDTH-1:0]        o_tot_I;
    wire [CNT_WIDTH-1:0]        o_err_Q;
    wire [CNT_WIDTH-1:0]        o_tot_Q;

    control #(.N_PHASES(N_PHASES)
        ) u_control (
        .clk(clock),
        .i_rst_n(i_reset),
        .i_sw(i_sw),
        .en_tx(en_tx),
        .en_rx(en_rx),
        .phase_sw(phase_sw),
        .reset_ber(reset_ber));

    wire [$clog2(N_PHASES)-1:0] phase_cnt;
    wire valid;

    freq_divider #(.N_PHASES(N_PHASES)
        ) u_div (
        .clk(clock),
        .i_rst_n(i_reset),
        .en_tx(en_tx),
        .phase_cnt(phase_cnt),
        .valid(valid));

    wire prbs_bit_I, prbs_bit_Q;

    prbs9 #(.SEED(SEED_I)
        ) u_prbs_I (
        .prbs_bit(prbs_bit_I),
        .clk(clock),
        .i_rst_n(i_reset),
        .en_tx(en_tx),
        .prbs_en(valid));

    prbs9 #(.SEED(SEED_Q)
        ) u_prbs_Q (
        .prbs_bit(prbs_bit_Q),
        .clk(clock),
        .i_rst_n(i_reset),
        .en_tx(en_tx),
        .prbs_en(valid));

    rc_tx #(.NB_COEFF(NB_COEFF),
            .NBF_COEFF(NBF_COEFF),
            .N_BAUDS(N_BAUDS),
            .N_PHASES(N_PHASES)
        ) u_rc_I (
        .clk(clock),
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
        .clk(clock),
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
        .clk(clock),
        .i_rst_n(i_reset),
        .en_rx(en_rx),
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
        .clk(clock),
        .i_rst_n(i_reset),
        .reset_ber(reset_ber),
        .phase_sw(phase_sw),
        .valid_dec(valid_dec),
        .dec_bit(dec_bit_I),
        .o_err(o_err_I),
        .o_tot(o_tot_I));

    ber_counter #(.SEED(SEED_Q),
                .CNT_WIDTH(CNT_WIDTH),
                .N_PHASES(N_PHASES)
    ) u_ber_Q (
        .clk(clock),
        .i_rst_n(i_reset),
        .reset_ber(reset_ber),
        .phase_sw(phase_sw),
        .valid_dec(valid_dec),
        .dec_bit(dec_bit_Q),
        .o_err(o_err_Q),
        .o_tot(o_tot_Q)
    );

    vio
     u_vio
       (
        .clk_0(clock),
        .probe_out0_0(i_sw),
        .probe_out1_0(i_reset)
        );
    
    ila
     u_ila
       (
        .clk_0(clock),
        .probe0_0(o_sample_I),
        .probe1_0(o_sample_Q),
        .probe2_0(o_led),
        .probe3_0(o_err_I),
        .probe4_0(o_tot_I),
        .probe5_0(o_err_Q),
        .probe6_0(o_tot_Q),
        .probe7_0(o_ber_ok)
	    );
    
    assign o_ber_ok = (o_tot_I > 0) && (o_err_I == 0) && (o_tot_Q > 0) && (o_err_Q == 0);
    assign o_led = {en_rx, en_tx, phase_sw};
endmodule