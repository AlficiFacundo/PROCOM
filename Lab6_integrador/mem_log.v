`timescale 1ns / 1ps

module mem_log #(
    parameter DATA_W = 32,
    parameter ADDR_W = 15                 // 2^15 = 32Kb
)(
    input  wire                clk,
    input  wire                i_rst_n,

    input  wire                o_run_log,
    input  wire                o_read_log,
    input  wire [ADDR_W-1:0]   o_addr_log_to_mem,
    input  wire [DATA_W-1:0]   i_wr_data,

    output wire [DATA_W-1:0]   i_data_log_from_mem,
    output reg                 i_mem_full
);
    reg              run_log_d;
    wire             run_log_rise = o_run_log & ~run_log_d;
    reg              logging;
    reg [ADDR_W-1:0] wr_addr;

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            run_log_d  <= 1'b0;
            logging    <= 1'b0;
            wr_addr    <= {ADDR_W{1'b0}};
            i_mem_full <= 1'b0;
        end else begin
            run_log_d <= o_run_log;

            if (run_log_rise) begin
                logging    <= 1'b1;
                wr_addr    <= {ADDR_W{1'b0}};
                i_mem_full <= 1'b0;
            end else if (logging) begin
                if (wr_addr == {ADDR_W{1'b1}}) begin
                    logging    <= 1'b0;
                    i_mem_full <= 1'b1;
                end else begin
                    wr_addr <= wr_addr + 1'b1;
                end
            end
        end
    end

    parameter RAM_WIDTH = DATA_W;                    // Specify RAM data width
    parameter RAM_DEPTH = (1<<ADDR_W);               // Specify RAM depth (number of entries)
    parameter RAM_PERFORMANCE = "LOW_LATENCY";       // "HIGH_PERFORMANCE" o "LOW_LATENCY"
    parameter INIT_FILE = "";                        

    wire [clogb2(RAM_DEPTH-1)-1:0] addra = wr_addr;             // bus de direccion de escritura
    wire [clogb2(RAM_DEPTH-1)-1:0] addrb = o_addr_log_to_mem;   // bus de direccion de lectura
    wire [RAM_WIDTH-1:0]           dina  = i_wr_data;           // dato de entrada
    wire                            clka  = clk;                // clock
    wire                            wea   = logging;            // write enable
    wire                            enb   = o_read_log;         // read enable
    wire                            rstb  = ~i_rst_n;           // reset de salida
    wire                            regceb = 1'b1;              // register enable de salida
    wire [RAM_WIDTH-1:0]            doutb;                      // dato de salida
    reg [RAM_WIDTH-1:0] BRAM [RAM_DEPTH-1:0];
    reg [RAM_WIDTH-1:0] ram_data = {RAM_WIDTH{1'b0}};

    // Inicializacion de la memoria
    generate
      if (INIT_FILE != "") begin: use_init_file
        initial
          $readmemh(INIT_FILE, BRAM, 0, RAM_DEPTH-1);
      end else begin: init_bram_to_zero
        integer ram_index;
        initial
          for (ram_index = 0; ram_index < RAM_DEPTH; ram_index = ram_index + 1)
            BRAM[ram_index] = {RAM_WIDTH{1'b0}};
      end
    endgenerate

    always @(posedge clka) begin
      if (wea)
        BRAM[addra] <= dina;
      if (enb)
        ram_data <= BRAM[addrb];
    end

    // HIGH_PERFORMANCE o LOW_LATENCY
    generate
      if (RAM_PERFORMANCE == "LOW_LATENCY") begin: no_output_register
        assign doutb = ram_data;
      end else begin: output_register
        reg [RAM_WIDTH-1:0] doutb_reg = {RAM_WIDTH{1'b0}};
        always @(posedge clka)
          if (rstb)
            doutb_reg <= {RAM_WIDTH{1'b0}};
          else if (regceb)
            doutb_reg <= ram_data;
        assign doutb = doutb_reg;
      end
    endgenerate

    assign i_data_log_from_mem = doutb;

    function integer clogb2;
      input integer depth;
        for (clogb2=0; depth>0; clogb2=clogb2+1)
          depth = depth >> 1;
    endfunction

endmodule