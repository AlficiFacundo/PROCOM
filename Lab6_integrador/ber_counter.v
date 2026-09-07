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
    wire      ref_bit = ref_lfsr[0];

    // Un paso y dos pasos del LFSR, precalculados. Hacen falta los dos porque
    // en el ciclo de un cambio de fase puede coincidir una muestra a contar
    // con la compensación: esa muestra pertenece a la fase vieja y se compara
    // normalmente, y ademas hay que adelantar uno para las que vienen.
    wire [8:0] lfsr_x1 = {ref_lfsr[0] ^ ref_lfsr[4], ref_lfsr[8:1]};
    wire [8:0] lfsr_x2 = {lfsr_x1[0]  ^ lfsr_x1[4],  lfsr_x1[8:1]};

    reg [3:0] pending;
    reg [3:0] last_delay;
    reg       last_delay_valid;

    wire [3:0] new_delay = delay_of_phase(phase_sw);

    wire       cambio    = last_delay_valid && (new_delay != last_delay);
    wire       adelantar = cambio && (new_delay <  last_delay);
    wire [3:0] retener   = (cambio && (new_delay > last_delay))
                           ? (new_delay - last_delay) : 4'd0;

    // reset_ber solo borra las estadisticas. no puede frenar el avance del
    // ref_lfsr ni el descuento de pending: control.v lo emite un ciclo
    // despues del cambio de fase, y si justo cae sobre un valid_dec esa
    // muestra quedaba sin procesar y el enlace se corria un simbolo.
    wire contar    = valid_dec && (pending == 4'd0);
    wire descontar = valid_dec && (pending != 4'd0);

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            ref_lfsr          <= SEED;
            pending           <= 4'd0;
            last_delay        <= 4'd0;
            last_delay_valid  <= 1'b0;
            o_err             <= {CNT_WIDTH{1'b0}};
            o_tot             <= {CNT_WIDTH{1'b0}};
        end else begin
            if (adelantar && contar)
                ref_lfsr <= lfsr_x2;
            else if (adelantar || contar)
                ref_lfsr <= lfsr_x1;

            if (!last_delay_valid)
                pending <= new_delay;                       
            else
                pending <= pending + retener - (descontar ? 4'd1 : 4'd0);

            last_delay       <= new_delay;
            last_delay_valid <= 1'b1;

            if (reset_ber) begin
                o_err <= {CNT_WIDTH{1'b0}};
                o_tot <= {CNT_WIDTH{1'b0}};
            end else if (contar) begin
                if (dec_bit != ref_bit)
                    o_err <= (&o_err) ? o_err : o_err + 1'b1;
                o_tot <= (&o_tot) ? o_tot : o_tot + 1'b1;
            end
        end
    end
endmodule