`timescale 1ns / 1ps
//-----------------------------------------------------------------------------
// GPIO de salida del uP (32 bits): {command[31:24], enable[23], data[22:0]}
// El uP "strobea" un registro escribiendo: valor(E=0) -> valor(E=1) -> valor(E=0)
// El flanco ascendente de "enable" es lo que carga el registro seleccionado por "command".
//-----------------------------------------------------------------------------
module register_file #(
    parameter CNT_WIDTH  = 64,
    parameter ADDR_LOG_W = 15,
    parameter DATA_W     = 32
)(
    input  wire                  clk,
    input  wire                  i_rst_n,

    // Interfaz con el uP (GPIO)
    input  wire [DATA_W-1:0]     i_gpo,
    output reg  [DATA_W-1:0]     o_gpi,

    // Hacia el DSP
    output reg                   o_rst,
    output reg                   o_enb_tx,
    output reg                   o_enb_rx,
    output reg  [1:0]            o_phase_sel,
    output reg                   o_run_log,
    output reg                   o_read_log,
    output reg  [ADDR_LOG_W-1:0] o_addr_log_to_mem,
    output wire                  o_ber_rst,

    // Desde el DSP / devices
    input  wire [DATA_W-1:0]     i_data_log_from_mem,
    input  wire                  i_mem_full,
    input  wire [CNT_WIDTH-1:0]  i_ber_samp_I,
    input  wire [CNT_WIDTH-1:0]  i_ber_samp_Q,
    input  wire [CNT_WIDTH-1:0]  i_ber_error_I,
    input  wire [CNT_WIDTH-1:0]  i_ber_error_Q,
    input  wire [3:0]            i_sw
);

    localparam CMD_NOP     = 8'h00;
    localparam CMD_RST     = 8'h01;
    localparam CMD_ENB_TX  = 8'h02;
    localparam CMD_ENB_RX  = 8'h03;
    localparam CMD_PHASE   = 8'h04;
    localparam CMD_RUN_LOG = 8'h05;
    localparam CMD_RD_LOG  = 8'h06;
    localparam CMD_ADDR    = 8'h07;
    localparam CMD_RD_SEL  = 8'h08;
    localparam CMD_BER_RST = 8'h09;

    wire [7:0]  command = i_gpo[31:24];
    wire [22:0] data    = i_gpo[22:0];

    // Sincronizador de 2 etapas para 'enable' (cruce de dominio de clock:
    // el GPIO del uP puede correr en un clock distinto al del RF/DSP).
    reg [2:0] enable_sync;
    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n)
            enable_sync <= 3'b000;
        else
            enable_sync <= {enable_sync[1:0], i_gpo[23]};
    end
    wire enable_rise = enable_sync[1] & ~enable_sync[2];

    // Pulso de 1 ciclo, independiente del reset_ber automatico por cambio de fase
    assign o_ber_rst = enable_rise & (command == CMD_BER_RST);

    reg [3:0]  rd_sel;

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            o_rst             <= 1'b0;
            o_enb_tx          <= 1'b0;
            o_enb_rx          <= 1'b0;
            o_phase_sel       <= 2'b00;
            o_run_log         <= 1'b0;
            o_read_log        <= 1'b0;
            o_addr_log_to_mem <= {ADDR_LOG_W{1'b0}};
            rd_sel            <= 4'h0;
        end else begin
            if (enable_rise) begin
                case (command)
                    CMD_RST:     o_rst             <= data[0];
                    CMD_ENB_TX:  o_enb_tx          <= data[0];
                    CMD_ENB_RX:  o_enb_rx          <= data[0];
                    CMD_PHASE:   o_phase_sel       <= data[1:0];
                    CMD_RUN_LOG: o_run_log         <= data[0];
                    CMD_RD_LOG:  o_read_log        <= data[0];
                    CMD_ADDR:    o_addr_log_to_mem <= data[ADDR_LOG_W-1:0];
                    CMD_RD_SEL:  rd_sel            <= data[3:0];
                    default: ;
                endcase
            end
        end
    end

    always @(*) begin
        case (rd_sel)
            4'h0: o_gpi = i_data_log_from_mem;
            4'h1: o_gpi = {{(DATA_W-1){1'b0}}, i_mem_full};
            4'h2: o_gpi = i_ber_samp_I[31:0];
            4'h3: o_gpi = i_ber_samp_I[63:32];
            4'h4: o_gpi = i_ber_samp_Q[31:0];
            4'h5: o_gpi = i_ber_samp_Q[63:32];
            4'h6: o_gpi = i_ber_error_I[31:0];
            4'h7: o_gpi = i_ber_error_I[63:32];
            4'h8: o_gpi = i_ber_error_Q[31:0];
            4'h9: o_gpi = i_ber_error_Q[63:32];
            4'hA: o_gpi = {{(DATA_W-4){1'b0}}, i_sw};
            4'hB: o_gpi = {{(DATA_W-22){1'b0}}, o_addr_log_to_mem, o_read_log,
                           o_run_log, o_phase_sel, o_enb_rx, o_enb_tx, o_rst};
            4'hC: o_gpi = 32'hC0FFEE01; //version (id) del codigo para verificar bitstream
            default: o_gpi = {DATA_W{1'b0}};
        endcase
    end

endmodule