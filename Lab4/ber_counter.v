module ber_counter #(
    parameter [8:0] SEED       = 9'h1AA,
    parameter       CNT_WIDTH  = 24,
    parameter       N_PHASES   = 4
)(
    input  wire                          clk,
    input  wire                          i_rst_n,
    input  wire                          reset_ber,   // pulso: cambio de fase
    input  wire [$clog2(N_PHASES)-1:0]   phase_sw,
    input  wire                          valid_dec,
    input  wire                          dec_bit,
    output reg  [CNT_WIDTH-1:0]          o_err,
    output reg  [CNT_WIDTH-1:0]          o_tot
);
    function automatic [3:0] delay_of_phase;
        input [1:0] ph;
        begin
            case (ph)
                2'd0: delay_of_phase = 4'd3;
                2'd1: delay_of_phase = 4'd3;
                2'd2: delay_of_phase = 4'd2;
                default: delay_of_phase = 4'd2; // fase 3
            endcase
        end
    endfunction

    reg [8:0] ref_lfsr;
    wire      ref_fb  = ref_lfsr[0] ^ ref_lfsr[4];
    wire      ref_bit = ref_lfsr[0];

    reg [3:0] pending;
    reg [3:0] last_delay;
    reg       last_delay_valid;

    wire [3:0] new_delay = delay_of_phase(phase_sw);

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            ref_lfsr          <= SEED;
            pending           <= 4'd0;
            last_delay        <= 4'd0;
            last_delay_valid  <= 1'b0;
            o_err             <= {CNT_WIDTH{1'b0}};
            o_tot             <= {CNT_WIDTH{1'b0}};
        end else begin

            //resincronizacion ante cambio de fase/delay
            if (!last_delay_valid) begin
                pending <= new_delay;                                   // arranque
            end else if (new_delay != last_delay) begin
                if (new_delay > last_delay)
                    pending  <= pending + (new_delay - last_delay);     // retener
                else
                    ref_lfsr <= {ref_fb, ref_lfsr[8:1]};                 // adelantar 1
            end
            last_delay       <= new_delay;
            last_delay_valid <= 1'b1;

            //reset de estadisticas (con prioridad sobre la captura)
            if (reset_ber) begin
                o_err <= {CNT_WIDTH{1'b0}};
                o_tot <= {CNT_WIDTH{1'b0}};
            end else if (valid_dec) begin
                if (pending > 0) begin
                    pending <= pending - 1'b1;
                end else begin
                    ref_lfsr <= {ref_fb, ref_lfsr[8:1]};
                    if (dec_bit != ref_bit)
                        o_err <= (&o_err) ? o_err : o_err + 1'b1;
                    o_tot <= (&o_tot) ? o_tot : o_tot + 1'b1;
                end
            end
        end
    end
endmodule