module control #(
    parameter N_PHASES = 4
)(
    input  wire                        clk,
    input  wire                        i_rst_n,
    input  wire [3:0]                  i_sw,
    output wire                        en_tx,
    output wire                        en_rx,
    output wire [$clog2(N_PHASES)-1:0] phase_sw,
    output reg                         reset_ber
);
    assign en_tx    = i_sw[0];
    assign en_rx    = i_sw[1];
    assign phase_sw = i_sw[3:2];

    reg [$clog2(N_PHASES)-1:0] phase_prev;
    reg                        phase_prev_valid;

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            phase_prev       <= 0;
            phase_prev_valid <= 1'b0;
            reset_ber        <= 1'b0;
        end else begin
            reset_ber        <= phase_prev_valid && (phase_sw != phase_prev);
            phase_prev       <= phase_sw;
            phase_prev_valid <= 1'b1;
        end
    end
endmodule